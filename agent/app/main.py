import json
import uuid

import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.llm import stream_chat

app = FastAPI()


def sse(event: str, data: dict) -> str:
    """Форматирует данные для SSE."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/ping")
async def ping():
    return {"answer": "pong"}


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat(request: ChatRequest):
    run_id = str(uuid.uuid4())
    async def events():
        yield sse("start", {"run_id": run_id})
        messages = [
            {"role": "system", "content": "Ты полезный помощник. Отвечай на русском."},
            {"role": "user", "content": request.message},
        ]
        try:
            async for chunk in stream_chat(messages):
                yield sse("delta", {"text": chunk})
            yield sse("done", {"status": "completed"})
        except httpx.HTTPError as e:
            yield sse("error", {"message": "Модель недоступна."})

    return StreamingResponse(events(), media_type="text/event-stream")
