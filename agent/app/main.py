import asyncio
import json
import logging
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.harness import run_agent


logger = logging.getLogger("uvicorn.error")

app = FastAPI()
conversations: dict[str, list[dict]] = {}
runs: dict[str, asyncio.Task] = {}  # run_id -> задача
active_runs: dict[str, str] = {}  # conversation_id -> run_id, кто сейчас выполняется

TERMINAL_EVENTS = {"done", "error", "cancelled"}


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
    conversation_id = request.conversation_id
    if conversation_id is None or conversation_id not in conversations:
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = []

    if conversation_id in active_runs:
        raise HTTPException(status_code=409, detail="В этом диалоге уже выполняется запрос")

    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    def emit(event: str, data: dict) -> None:
        queue.put_nowait((event, data))  # положить событие в очередь не дожидаясь

    task = asyncio.create_task(
        run_agent(run_id, conversations[conversation_id], request.message, emit)
    )
    runs[run_id] = task
    active_runs[conversation_id] = run_id

    async def events():
        try:
            yield sse("start", {"run_id": run_id, "conversation_id": conversation_id})
            while True:
                event, data = await queue.get()
                yield sse(event, {"run_id": run_id, **data})
                if event in TERMINAL_EVENTS:
                    break
        finally:
            if not task.done():
                task.cancel()  # клиент ушёл, остановка
            runs.pop(run_id, None)
            active_runs.pop(conversation_id, None)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    task = runs.get(run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Выполнение не найдено или уже завершено")
    task.cancel()
    return {"status": "cancelling", "run_id": run_id}