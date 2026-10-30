import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import app.mcp_client as mcp_client


class FakeSession:
    """Подменяет MCP-сессию с FreePeak."""

    def __init__(self, tool_names=(), result=None):
        self.tool_names = tool_names
        self.result = result
        self.calls = []

    async def list_tools(self):
        tools = [
            SimpleNamespace(name=n, description="", input_schema={"type": "object"})
            for n in self.tool_names
        ]
        return SimpleNamespace(tools=tools)

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


def mcp_result(text, is_error=False):
    """Ответ FreePeak: текст результата и признак ошибки."""
    return SimpleNamespace(is_error=is_error, content=[SimpleNamespace(text=text)])


def patch_session(monkeypatch, session):
    @asynccontextmanager
    async def fake_mcp_session():
        yield session

    monkeypatch.setattr(mcp_client, "mcp_session", fake_mcp_session)


def test_only_allowed_tools_are_given_to_model(monkeypatch):
    session = FakeSession(["schema_sales", "describe_sales", "query_sales", "execute_sales", "transaction_sales"])
    patch_session(monkeypatch, session)

    tools = asyncio.run(mcp_client.list_mcp_tools())

    names = {t["function"]["name"] for t in tools}
    assert names == {"schema_sales", "describe_sales", "query_sales"}
    assert all(t["type"] == "function" for t in tools)


def test_forbidden_tool_is_not_executed(monkeypatch):
    session = FakeSession()
    patch_session(monkeypatch, session)

    result = asyncio.run(mcp_client.call_mcp_tool("execute_sales", {"query": "DELETE FROM sales"}))

    assert result["error"] == "forbidden_tool"
    assert session.calls == []


def test_success_returns_text(monkeypatch):
    session = FakeSession(result=mcp_result("revenue\n36200.00"))
    patch_session(monkeypatch, session)

    result = asyncio.run(mcp_client.call_mcp_tool("query_sales", {"query": "SELECT 1"}))

    assert "error" not in result
    assert "36200.00" in result["result"]
    assert session.calls == [("query_sales", {"query": "SELECT 1"})]


def test_sql_error_becomes_mcp_error(monkeypatch):
    session = FakeSession(result=mcp_result('relation "nope" does not exist', is_error=True))
    patch_session(monkeypatch, session)

    result = asyncio.run(mcp_client.call_mcp_tool("query_sales", {"query": "SELECT * FROM nope"}))

    assert result["error"] == "mcp_error"
    assert "does not exist" in result["message"]


def test_server_down_becomes_mcp_unavailable(monkeypatch):
    @asynccontextmanager
    async def broken_session():
        raise ConnectionError("FreePeak выключен")
        yield

    monkeypatch.setattr(mcp_client, "mcp_session", broken_session)

    result = asyncio.run(mcp_client.call_mcp_tool("query_sales", {"query": "SELECT 1"}))

    assert result["error"] == "mcp_unavailable"


def test_slow_server_becomes_mcp_timeout(monkeypatch):
    class SlowSession(FakeSession):
        async def call_tool(self, name, arguments):
            await asyncio.sleep(5)

    patch_session(monkeypatch, SlowSession())
    monkeypatch.setattr(mcp_client, "MCP_TIMEOUT", 0.05)

    result = asyncio.run(mcp_client.call_mcp_tool("query_sales", {"query": "SELECT 1"}))

    assert result["error"] == "mcp_timeout"


def test_write_query_is_rejected_before_mcp(monkeypatch):
    session = FakeSession()
    patch_session(monkeypatch, session)

    result = asyncio.run(mcp_client.call_mcp_tool("query_sales", {"query": "DELETE FROM sales"}))

    assert result["error"] == "read_only"
    assert session.calls == []