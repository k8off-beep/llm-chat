import os
import json

import httpx

LLM_URL = os.getenv("LLM_URL", "http://host.docker.internal:8080")


async def stream_chat(messages: list[dict], tools=None):
    """Отправляет историю в llama-server.

    Отдаёт словари:
    - {"type": "text", "text": "..."} — кусочки текста, по мере генерации;
    - {"type": "tool_calls", "tool_calls": [...]} — в конце, если модель вызвала инструменты.
    """
    body = {
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
    }
    if tools:
        body["tools"] = tools

    url = f"{LLM_URL}/v1/chat/completions"
    calls = {}

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                chunk = json.loads(data)  # превращает текст в питоновский словарь
                if not chunk.get("choices"):
                    continue
                delta = chunk["choices"][0]["delta"]

                content = delta.get("content")
                if content:
                    yield {"type": "text", "text": content}

                for part in delta.get("tool_calls") or []:
                    entry = calls.setdefault(
                        part["index"], {"id": None, "name": "", "arguments": ""}
                    )
                    if part.get("id"):
                        entry["id"] = part["id"]
                    function = part.get("function", {})
                    if function.get("name"):
                        entry["name"] = function["name"]
                    if function.get("arguments"):
                        entry["arguments"] += function["arguments"]
    if calls:
        yield {"type": "tool_calls", "tool_calls": [calls[i] for i in sorted(calls)]}
