import json
import uuid
import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.llm import stream_chat

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
        messages = ([{"role": "system", "content": "Ты полезный помощник. Отвечай на русском."}]
                    + history
                    + [{"role": "user", "content": request.message}]
                )
        try:
            answer = ""
            logger.info("run_id=%s conversation_id=%s сообщений в контексте: %d",
                        run_id, conversation_id, len(messages))
            async for chunk in stream_chat(messages):
                answer += chunk
                yield sse("delta", {"text": chunk})
            history.append({"role": "user", "content": request.message})
            history.append({"role": "assistant", "content": answer})
            yield sse("done", {"status": "completed"})
        except httpx.HTTPError:
            logger.exception("Ошибка при обращении к модели, run_id=%s", run_id)
            yield sse("error", {"message": "Ошибка при обращении к модели."})

    return StreamingResponse(events(), media_type="text/event-stream")
