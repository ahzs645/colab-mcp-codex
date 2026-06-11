# Copyright 2026 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Static MCP proxy for clients that do not refresh dynamic Colab tools.

The regular Colab MCP server exposes notebook tools after the browser
connection is established and notifies the client with tools/list_changed.
Some clients do not surface that refreshed tool list. This server exposes a
small stable tool set up front and forwards calls to the connected Colab
notebook tools internally.
"""

import asyncio
from contextlib import AsyncExitStack
from typing import Any
import webbrowser

from fastmcp import FastMCP

from colab_mcp.session import ColabProxyClient, UI_CONNECTION_TIMEOUT
from colab_mcp.websocket_server import COLAB, SCRATCH_PATH, ColabWebSocketServer


mcp = FastMCP(
    name="ColabStaticProxy",
    instructions=(
        "Static proxy for Google Colab MCP. Use open_colab_browser_connection, "
        "then colab_list_tools, then colab_call_tool with a downstream tool name."
    ),
)

_wss: ColabWebSocketServer | None = None
_proxy_client: ColabProxyClient | None = None
_exit_stack: AsyncExitStack | None = None


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


async def _ensure_started() -> None:
    global _exit_stack, _proxy_client, _wss
    if _proxy_client is not None:
        return

    _exit_stack = AsyncExitStack()
    _wss = await _exit_stack.enter_async_context(ColabWebSocketServer())
    _proxy_client = await _exit_stack.enter_async_context(ColabProxyClient(_wss))


def _require_proxy() -> ColabProxyClient:
    if _proxy_client is None:
        raise RuntimeError("Colab proxy has not started yet.")
    return _proxy_client


@mcp.tool
async def open_colab_browser_connection() -> bool:
    """Open/connect a Google Colab browser session for MCP control."""
    await _ensure_started()
    proxy = _require_proxy()
    if proxy.is_connected():
        return True

    assert _wss is not None
    webbrowser.open_new(
        f"{COLAB}{SCRATCH_PATH}#mcpProxyToken={_wss.token}&mcpProxyPort={_wss.port}"
    )
    await proxy.await_proxy_connection()
    return proxy.is_connected()


@mcp.tool
async def colab_connection_status() -> dict[str, Any]:
    """Return whether the Colab browser session is connected."""
    await _ensure_started()
    proxy = _require_proxy()
    assert _wss is not None
    return {
        "connected": proxy.is_connected(),
        "port": _wss.port,
        "connect_url": (
            f"{COLAB}{SCRATCH_PATH}#mcpProxyToken={_wss.token}"
            f"&mcpProxyPort={_wss.port}"
        ),
        "timeout_seconds": UI_CONNECTION_TIMEOUT,
    }


@mcp.tool
async def colab_list_tools() -> list[dict[str, Any]]:
    """List downstream tools exposed by the connected Colab notebook session."""
    await _ensure_started()
    proxy = _require_proxy()
    if not proxy.is_connected() or proxy.proxy_mcp_client is None:
        raise RuntimeError(
            "Colab is not connected. Call open_colab_browser_connection first."
        )

    tools = await proxy.proxy_mcp_client.list_tools()
    return [tool.model_dump(mode="json", exclude_none=True) for tool in tools]


@mcp.tool
async def colab_call_tool(
    name: str, arguments: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call a downstream Colab notebook MCP tool by name with JSON arguments."""
    await _ensure_started()
    proxy = _require_proxy()
    if not proxy.is_connected() or proxy.proxy_mcp_client is None:
        raise RuntimeError(
            "Colab is not connected. Call open_colab_browser_connection first."
        )

    result = await proxy.proxy_mcp_client.call_tool(name, arguments or {})
    return {
        "is_error": result.is_error,
        "data": _to_jsonable(result.data),
        "content": _to_jsonable(getattr(result, "content", None)),
        "structured_content": _to_jsonable(
            getattr(result, "structured_content", None)
        ),
        "meta": _to_jsonable(getattr(result, "meta", None)),
    }


async def main_async() -> None:
    await _ensure_started()
    try:
        await mcp.run_async()
    finally:
        if _exit_stack is not None:
            await _exit_stack.aclose()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
