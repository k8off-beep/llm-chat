import os
import json

import httpx

LLM_URL = os.getenv("LLM_URL", "http://host.docker.internal:8080")


async def stream_chat(messages: list[dict]):
    """Отправляет историю в llama-server и отдаёт текст ответа по кусочкам."""
    body = {
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
    }
    url = f"{LLM_URL}/v1/chat/completions"
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                data = json.loads(data)
                if "choices" in data and len(data["choices"]) > 0:
                    delta = data["choices"][0]["delta"]
                    content = delta.get("content")
                    if content:
                        yield content