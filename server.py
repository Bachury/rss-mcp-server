"""RSS MCP Server - Fetch and parse RSS feeds via MCP tools."""

import json
import asyncio
from typing import Optional

# 🔥 🔥 🔥 全局强制：使用环境已有的 asyncio 循环（彻底根治报错）
def get_running_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

asyncio.get_event_loop = get_running_loop
asyncio.get_running_loop = get_running_loop

from mcp.server.fastmcp import FastMCP

from rss_fetcher import fetch_single_feed, fetch_multiple_feeds, load_feeds_config

# 🔥 关键：不要让 FastMCP 自动启动！
mcp = FastMCP("RSS News Fetcher", auto_start=False)

@mcp.tool()
async def fetch_rss(url: str, limit: int = 10) -> str:
    """获取单个 RSS 源的最新文章。"""
    result = await fetch_single_feed(url=url, limit=limit)
    return json.dumps(result, ensure_ascii=False, indent=2)

@mcp.tool()
async def fetch_all_feeds(
    category: Optional[str] = None, limit_per_feed: int = 5
) -> str:
    """从预配置的 RSS 源列表批量获取最新文章。"""
    results = await fetch_multiple_feeds(
        category=category, limit_per_feed=limit_per_feed
    )
    return json.dumps(list(results), ensure_ascii=False, indent=2)

@mcp.tool()
async def fetch_custom_feeds(urls: list[str], limit_per_feed: int = 5) -> str:
    """从自定义的 RSS URL 列表批量获取文章。"""
    results = await fetch_multiple_feeds(urls=urls, limit_per_feed=limit_per_feed)
    return json.dumps(list(results), ensure_ascii=False, indent=2)

@mcp.tool()
async def list_feeds() -> str:
    """列出所有预配置的 RSS 源信息。"""
    feeds = load_feeds_config()
    return json.dumps(feeds, ensure_ascii=False, indent=2)

# 🔥 🔥 🔥 最终启动：完全接管，不依赖 fastmcp cli
if __name__ == "__main__":
    import uvicorn
    from fastmcp.server.server import MCPServer
    server = MCPServer(mcp)
    uvicorn.run(server.app, host="0.0.0.0", port=8081)
