import json
import logging
import os
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


from app.llm import stream_chat
from app.prompts import SYSTEM_PROMPT
from app.tools import TOOLS, execute_tool


SYSTEM_MESSAGE = {"role": "system", "content": SYSTEM_PROMPT}
MAX_LLM_CALLS = int(os.getenv("MAX_LLM_CALLS", "5"))

logger = logging.getLogger("uvicorn.error")

app = FastAPI()
conversations: dict[str, list[dict]] = {}


def sse(event: str, data: dict) -> str:
    """Форматирует данные для SSE."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/ping")
async def ping():
    return {"answer": "pong"}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    return conversations[conversation_id]


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@app.post("/api/chat")
async def chat(request: ChatRequest):
    run_id = str(uuid.uuid4())
    conversation_id = request.conversation_id
    if conversation_id is None or conversation_id not in conversations:
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = []
    async def events():
        yield sse("start", {"run_id": run_id, "conversation_id": conversation_id})
        history = conversations[conversation_id]
        seen_calls = set()

        new_messages = [{"role": "user", "content": request.message}]

        try:
            for step in range(MAX_LLM_CALLS):
                messages = [SYSTEM_MESSAGE] + history + new_messages
                answer = ""
                tool_calls = None

                async for event in stream_chat(messages, tools=TOOLS):
                    if event["type"] == "text":
                        answer += event["text"]
                        yield sse("delta", {"text": event["text"]})
                    elif event["type"] == "tool_calls":
                        tool_calls = event["tool_calls"]
                if not tool_calls:
                    new_messages.append({"role": "assistant", "content": answer})
                    history.extend(new_messages)
                    yield sse("done", {"status": "completed"})
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
                    yield sse("tool", {"name": call["name"], "status": "running"})
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
                    yield sse("tool", {"name": call["name"], "status": "done"})

            yield sse("error", {"message": "Превышен лимит обращений к модели."})

        except httpx.HTTPError:
            logger.exception("Ошибка при обращении к модели, run_id=%s", run_id)
            yield sse("error", {"message": "Ошибка при обращении к модели."})

    return StreamingResponse(events(), media_type="text/event-stream")
