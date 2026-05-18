"""RSS MCP Server - Fetch and parse RSS feeds via MCP tools."""

import json
from typing import Optional
import asyncio

from mcp.server.fastmcp import FastMCP

from rss_fetcher import fetch_single_feed, fetch_multiple_feeds, load_feeds_config

mcp = FastMCP("RSS News Fetcher")

@mcp.tool()
async def fetch_rss(url: str, limit: int = 10) -> str:
    """获取单个 RSS 源的最新文章。

    Args:
        url: RSS feed 的 URL 地址
        limit: 返回的最大文章数量，默认 10
    """
    result = await fetch_single_feed(url=url, limit=limit)
    return json.dumps(result, ensure_ascii=False, indent=2)

@mcp.tool()
async def fetch_all_feeds(
    category: Optional[str] = None, limit_per_feed: int = 5
) -> str:
    """从预配置的 RSS 源列表批量获取最新文章。

    可按分类筛选：国内AI垂直、大厂官方博客、综合科技资讯、前沿论文与社区。

    Args:
        category: 可选的分类过滤，如 "国内AI垂直"、"大厂官方博客" 等。为空则获取全部源。
        limit_per_feed: 每个源返回的最大文章数量，默认 5
    """
    results = await fetch_multiple_feeds(
        category=category, limit_per_feed=limit_per_feed
    )
    return json.dumps(list(results), ensure_ascii=False, indent=2)

@mcp.tool()
async def fetch_custom_feeds(urls: list[str], limit_per_feed: int = 5) -> str:
    """从自定义的 RSS URL 列表批量获取文章。

    Args:
        urls: RSS feed URL 列表
        limit_per_feed: 每个源返回的最大文章数量，默认 5
    """
    results = await fetch_multiple_feeds(urls=urls, limit_per_feed=limit_per_feed)
    return json.dumps(list(results), ensure_ascii=False, indent=2)

@mcp.tool()
async def list_feeds() -> str:
    """列出所有预配置的 RSS 源信息（名称、分类、URL）。"""
    feeds = load_feeds_config()
    return json.dumps(feeds, ensure_ascii=False, indent=2)

# ----------------- 修复部分 -----------------
# 云函数/Lambda 入口（必须加）
def handler(event, context):
    try:
        # 获取已存在的事件循环，不新建！
        loop = asyncio.get_event_loop()
        # 后台启动 MCP 服务，不阻塞
        loop.create_task(mcp.run_server(transport="http", host="0.0.0.0", port=8082))
        return {"status": "success", "message": "RSS MCP server started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 本地运行（保留，方便你测试）
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8082)