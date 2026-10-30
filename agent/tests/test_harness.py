import asyncio
import json

import pytest

import app.harness as harness


QUERY_SALES_SPEC = {"type": "function", "function": {"name": "query_sales", "description": "", "parameters": {}}}


class FakeLLM:
    """Подменяет stream_chat: на каждый вызов отдаёт следующий заготовленный ответ."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []  # что harness отправил "модели" - потом проверяем

    async def __call__(self, messages, tools=None):
        self.calls.append({"messages": list(messages), "tools": tools})
        for event in self.replies.pop(0):
            yield event


def text(answer):
    """Ответ модели обычным текстом."""
    return [{"type": "text", "text": answer}, {"type": "finish", "reason": "stop"}]


def tool_call(name, arguments, call_id="call_1"):
    """Ответ модели вызовом инструмента. arguments - dict или уже готовая строка."""
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments)
    return [
        {"type": "tool_calls", "tool_calls": [{"id": call_id, "name": name, "arguments": arguments}]},
        {"type": "finish", "reason": "tool_calls"},
    ]


def patch(monkeypatch, llm, mcp_tools=(), mcp_result=None):
    """Подменяет модель и MCP. Возвращает список вызовов MCP, чтобы его проверять"""
    mcp_calls = []

    async def fake_list_mcp_tools():
        return list(mcp_tools)

    async def fake_call_mcp_tool(name, arguments):
        mcp_calls.append((name, arguments))
        return mcp_result or {"result": "ok"}

    monkeypatch.setattr(harness, "stream_chat", llm)
    monkeypatch.setattr(harness, "list_mcp_tools", fake_list_mcp_tools)
    monkeypatch.setattr(harness, "call_mcp_tool", fake_call_mcp_tool)
    return mcp_calls


def run(history=None):
    """Запускает агента и собирает все события в список"""
    events = []
    history = [] if history is None else history
    asyncio.run(harness.run_agent("test-run", history, "вопрос", lambda e, d: events.append((e, d))))
    return events, history


def test_plain_answer_saved_to_history(monkeypatch):
    patch(monkeypatch, FakeLLM(text("Привет!")))

    events, history = run()

    assert events[-1] == ("done", {"status": "completed"})
    assert history == [
        {"role": "user", "content": "вопрос"},
        {"role": "assistant", "content": "Привет!"},
    ]


def test_previous_history_is_sent_to_model(monkeypatch):
    llm =FakeLLM(text("ок"))
    patch(monkeypatch, llm)
    old = [{"role": "user", "content": "раньше"}, {"role": "assistant", "content": "ответ"}]

    run(history=old)

    sent = llm.calls[0]["messages"]
    assert sent[0]["role"] == "system"
    assert sent[1:3] == old[:2]


def test_local_tool_result_goes_back_to_model(monkeypatch):
    llm = FakeLLM(
        tool_call("find_submatrices", {"matrix": ["A1A1", "B2B2", "A1A1", "B2B2"], "pattern": ["A1", "B2"]}),
        text("Найдено 4"),
    )
    patch(monkeypatch, llm)

    events, history = run()

    assert len(llm.calls) == 2
    tool_message = llm.calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call_1"
    assert json.loads(tool_message["content"])["count"] == 4
    assert events[-1][0] == "done"


def test_invalid_arguments_do_not_crash(monkeypatch):
    llm = FakeLLM(tool_call("find_submatrices", '{"matrix": ['), text("Ошибка в данных"))
    patch(monkeypatch, llm)

    events, _ = run()

    tool_message = llm.calls[1]["messages"][-1]
    assert json.loads(tool_message["content"])["error"] == "invalid_arguments"
    assert events[-1][0] == "done"


def test_loop_limit_stops_run(monkeypatch):
    replies = [
        tool_call("find_submatrices", {"matrix": ["A1"], "pattern": ["A"]}, call_id=f"call_{i}")
        for i in range(20)
    ]
    llm = FakeLLM(*replies)
    patch(monkeypatch, llm)

    events, history = run()

    assert events[-1][0] == "error"
    assert len(llm.calls) <= harness.MAX_LLM_CALLS
    assert history == []


class HangingLLM:
    """Модель, которая начала отвечать и «задумалась» — её отменят посреди ответа."""

    def __init__(self):
        self.calls = 0

    async def __call__(self, messages, tools=None):
        self.calls += 1
        yield {"type": "text", "text": "Начинаю..."}
        await asyncio.sleep(60)
        yield {"type": "finish", "reason": "stop"}


def test_cancel_stops_run_and_keeps_history_clean(monkeypatch):
    llm = HangingLLM()
    patch(monkeypatch, llm)
    events, history = [], []

    async def scenario():
        task = asyncio.create_task(
            harness.run_agent("test-run", history, "вопрос", lambda e, d: events.append((e, d)))
        )
        await asyncio.sleep(0.1)       # даём агенту начать и получить первый кусок текста
        task.cancel()                  # то же, что делает POST /api/runs/{id}/cancel
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    assert ("delta", {"text": "Начинаю..."}) in events
    assert events[-1][0] == "cancelled"
    assert llm.calls == 1          # после отмены к модели больше не обращались
    assert history == []           # отменённый прогон не попал в контекст



def test_mcp_tool_is_called_with_parsed_arguments(monkeypatch):
    llm = FakeLLM(tool_call("query_sales", {"query": "SELECT 1"}), text("Готово"))
    mcp_calls = patch(monkeypatch, llm, mcp_tools=[QUERY_SALES_SPEC])

    events, _ = run()

    assert mcp_calls == [("query_sales", {"query": "SELECT 1"})]
    assert events[-1][0] == "done"


def test_unknown_tool_is_not_sent_to_mcp(monkeypatch):
    llm = FakeLLM(tool_call("execute_sql", {"query": "DROP TABLE sales"}), text("Нельзя"))
    mcp_calls = patch(monkeypatch, llm)

    run()

    assert mcp_calls == []
    tool_message = llm.calls[1]["messages"][-1]
    assert json.loads(tool_message["content"])["error"] == "unknown_tool"


def test_mcp_down_still_answers_with_local_tools(monkeypatch):
    llm = FakeLLM(text("Привет"))
    patch(monkeypatch, llm)

    async def broken_list():
        raise ConnectionError("FreePeak выключен")

    monkeypatch.setattr(harness, "list_mcp_tools", broken_list)

    events, _ = run()

    assert events[-1][0] == "done"
    names = [t["function"]["name"] for t in llm.calls[0]["tools"]]
    assert names == ["find_submatrices"]