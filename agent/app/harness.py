import asyncio
import json
import logging
import os

import httpx

from app.llm import stream_chat
from app.prompts import SYSTEM_PROMPT
from app.tools import TOOLS, execute_tool

logger = logging.getLogger("uvicorn.error")

SYSTEM_MESSAGE = {"role": "system", "content": SYSTEM_PROMPT}
MAX_LLM_CALLS = int(os.getenv("MAX_LLM_CALLS", "5"))


async def run_agent(run_id: str, history: list[dict], user_message: str, emit) -> None:
    """Цикл агента: модель → инструменты → модель, пока не будет итогового ответа.

    События отдаёт через emit(event, data). В историю пишет только при успехе.
    """
    new_messages = [{"role": "user", "content": user_message}]
    seen_calls = set()

    try:
        for step in range(MAX_LLM_CALLS):
            messages = [SYSTEM_MESSAGE] + history + new_messages
            answer = ""
            tool_calls = None

            async for event in stream_chat(messages, tools=TOOLS):
                if event["type"] == "text":
                    answer += event["text"]
                    emit("delta", {"text": event["text"]})
                elif event["type"] == "tool_calls":
                    tool_calls = event["tool_calls"]
            if not tool_calls:
                new_messages.append({"role": "assistant", "content": answer})
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
                logger.info("run_id=%s модель вызвала %s, аргументы: %s",
                            run_id, call["name"], call["arguments"])
                emit("tool", {"name": call["name"], "status": "running"})
                key = (call["name"], call["arguments"])
                if key in seen_calls:
                    result = {
                        "error": "duplicate_call",
                        "message": "Этот вызов уже выполнен, его результат есть выше. Не вызывай инструмент снова — сформируй ответ.",
                    }
                else:
                    seen_calls.add(key)
                    result = execute_tool(call["name"], call["arguments"])
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

    except Exception:
        logger.exception("run_id=%s непредвиденная ошибка", run_id)
        emit("error", {"message": "Внутренняя ошибка сервера."})