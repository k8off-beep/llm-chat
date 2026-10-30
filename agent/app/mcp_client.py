import asyncio
import logging
import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client


logger = logging.getLogger("uvicorn.error")

MCP_URL = os.getenv("MCP_URL", "http://host.docker.internal:9092/mcp")
MCP_API_KEY = os.getenv("MCP_API_KEY", "mcp_demo_key")
MCP_TIMEOUT = float(os.getenv("MCP_TIMEOUT", "10"))

ALLOWED_MCP_TOOLS = {"schema_sales", "describe_sales", "query_sales"}


@asynccontextmanager
async def mcp_session():
    """Открывает MCP-сессию с FreePeak и закрывает её по выходу."""
    async with create_mcp_http_client(headers={"Authorization": f"Bearer {MCP_API_KEY}"}) as http:
        async with streamable_http_client(MCP_URL, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


async def list_mcp_tools() -> list[dict]:
    """Возвращает разрешённые инструменты FreePeak в формате tools для модели."""
    async with mcp_session() as session:
        response = await session.list_tools()
    result_tools = []
    for tool in response.tools:
        if tool.name not in ALLOWED_MCP_TOOLS:
            continue
        tool_spec = {"type": "function",
                        "function": {"name": tool.name, "description": tool.description or "", "parameters": tool.input_schema}}
        result_tools.append(tool_spec)
    return result_tools


async def call_mcp_tool(name: str, arguments: dict) -> dict:
    """Выполняет разрешённый инструмент FreePeak. Всегда возвращает словарь."""
    if name not in ALLOWED_MCP_TOOLS:
        return {"error": "forbidden_tool", "message": "Запрещённый инструмент."}
    if name == "query_sales":
        query = str(arguments.get("query", "")).lstrip().lower()
        if not query.startswith(("select", "with")):
            return {
                "error": "read_only",
                "message": "Запрос должен начинаться с SELECT или WITH: разрешено только чтение данных.",
            }
    try:
        async with asyncio.timeout(MCP_TIMEOUT):
            async with mcp_session() as session:
                result = await session.call_tool(name, arguments)
        text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
        if result.is_error:
            return {"error": "mcp_error", "message": text}
        return {
            "result": text,
            "hint": "Покажи пользователю все строки результата с подписями столбцов. "
                    "Период называй так же, как в условии запроса. "
                    "После таблицы ничего не добавляй: никаких «Всего», подсчётов строк и выводов. "
                    "Если результат равен 0, напиши, что продаж в этом периоде нет.",
        }
    except TimeoutError:
        return {"error": "mcp_timeout", "message": "Превышено время ожидания."}
    except Exception:
        logger.exception("Ошибка вызова MCP-инструмента %s", name)
        return {"error": "mcp_unavailable", "message": "MCP сервер недоступен."}