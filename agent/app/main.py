import asyncio
import json
import uuid

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


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
        text = f"Вы написали: {request.message}. Это тестовый ответ без модели."
        for word in text.split():
            yield sse("delta", {"text": word + " "})
            await asyncio.sleep(0.3)  
        yield sse("done", {"status": "completed"})

    return StreamingResponse(events(), media_type="text/event-stream")
