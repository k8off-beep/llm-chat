import asyncio
import json
import logging
import os

import httpx

from app.llm import stream_chat
from app.mcp_client import ALLOWED_MCP_TOOLS, call_mcp_tool, list_mcp_tools
from app.prompts import SYSTEM_PROMPT
from app.tools import TOOLS, execute_tool

logger = logging.getLogger("uvicorn.error")

SYSTEM_MESSAGE = {"role": "system", "content": SYSTEM_PROMPT}
MAX_LLM_CALLS = int(os.getenv("MAX_LLM_CALLS", "5"))
RUN_TIMEOUT = float(os.getenv("RUN_TIMEOUT", "120"))
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "5"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "16000"))


async def run_agent(run_id: str, history: list[dict], user_message: str, emit) -> None:
    """Цикл агента: модель → инструменты → модель, пока не будет итогового ответа.

    События отдаёт через emit(event, data). В историю пишет только при успехе.
    """
    new_messages = [{"role": "user", "content": user_message}]
    seen_calls = set()

    try:
        async with asyncio.timeout(RUN_TIMEOUT):
            tools = list(TOOLS)
            try:
                tools += await list_mcp_tools()
            except Exception:
                logger.exception("run_id=%s не удалось получить инструменты MCP", run_id)

            tool_calls_count = 0
            for step in range(MAX_LLM_CALLS):
                messages = [SYSTEM_MESSAGE] + history + new_messages
                context_size = len(json.dumps(messages, ensure_ascii=False))
                if context_size > MAX_CONTEXT_CHARS:
                    emit("error", {"message": "Диалог слишком длинный для модели. Очистите чат и начните заново."})
                    return
                answer = ""
                tool_calls = None
                reason = None

                async for event in stream_chat(messages, tools=tools):
                    if event["type"] == "text":
                        answer += event["text"]
                        emit("delta", {"text": event["text"]})
                    elif event["type"] == "tool_calls":
                        tool_calls = event["tool_calls"]
                    elif event["type"] == "finish":
                        reason = event["reason"]
                if not tool_calls:
                    new_messages.append({"role": "assistant", "content": answer})
                    if reason == "length":
                        emit("error", {"message": "Ответ превысил лимит длины и был обрезан"})
                        return
                    history.extend(new_messages)
                    emit("done", {"status": "completed"})
                    return

                new_messages.append({
                    "role": "assistant",
                    "content": answer,
                    "tool_calls":[
                        {"id": c["id"], "type": "function",
                        "function": {"name": c["name"], "arguments": c["arguments"]}}
                        for c in tool_calls
                    ],
                })
                for call in tool_calls:
                    tool_calls_count += 1
                    if tool_calls_count > MAX_TOOL_CALLS:
                        emit("error", {"message": "Превышен лимит вызовов инструментов."})
                        return
                    logger.info("run_id=%s модель вызвала %s, аргументы: %s",
                                run_id, call["name"], call["arguments"])
                    emit("tool", {"name": call["name"], "status": "running", "arguments": call["arguments"]})
                    key = (call["name"], call["arguments"])
                    if key in seen_calls:
                        result = {
                            "error": "duplicate_call",
                            "message": "Этот вызов уже выполнен, его результат есть выше. Не вызывай инструмент снова — сформируй ответ.",
                        }
                    else:
                        seen_calls.add(key)
                        result = await run_tool(call["name"], call["arguments"])
                    logger.info("result=%s", result)
                    new_messages.append({"role": "tool", "tool_call_id": call["id"],
                                        "content": json.dumps(result, ensure_ascii=False)})
                    emit("tool", {"name": call["name"], "status": "done"})

            emit("error", {"message": "Превышен лимит обращений к модели."})

    except asyncio.CancelledError:
        logger.info("run_id=%s отменён", run_id)
        emit("cancelled", {"message": "Остановлено"})
        raise

    except httpx.HTTPError:
        logger.exception("run_id=%s ошибка при обращении к модели", run_id)
        emit("error", {"message": "Ошибка при обращении к модели."})

    except TimeoutError:
        logger.warning("run_id=%s превышено время выполнения", run_id)
        emit("error", {"message": f"Превышено время выполнения ({RUN_TIMEOUT:.0f} c)."})

    except Exception:
        logger.exception("run_id=%s непредвиденная ошибка", run_id)
        emit("error", {"message": "Внутренняя ошибка сервера."})


async def run_tool(name: str, arguments: str) -> dict:
    """функция направляет вызов в локальный инструмент или в MCP"""
    if name == "find_submatrices":
        return execute_tool(name, arguments)
    if name in ALLOWED_MCP_TOOLS:
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            return {"error": "invalid_arguments", "message": "Аргументы — не корректный JSON."}
        if not isinstance(args, dict):
            return {"error": "invalid_arguments", "message": "Аргументы должны быть JSON-объектом."}
        return await call_mcp_tool(name, args)
    return {"error": "unknown_tool", "message": "неизвестный инструмент"}