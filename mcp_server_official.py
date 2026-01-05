import asyncio
import sys
import os

# 确保能导入 backend
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from mcp.server.fastmcp import FastMCP # 官方 SDK 0.1.0+ 也引入了 FastMCP 接口，如果版本低则用基础 Server
# 为了最大兼容性，我们使用标准 Server 实现
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server

from backend.database import SessionLocal
from backend.models import Item, Feedback, ItemUser, User

# 初始化 Server
server = Server("feedback-system")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_system_stats",
            description="获取系统当前的统计数据（用户数、事项数）",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="search_items",
            description="根据关键词搜索事项及其反馈情况",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["keyword"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "get_system_stats":
        db = SessionLocal()
        try:
            user_count = db.query(User).count()
            item_count = db.query(Item).count()
            return [types.TextContent(type="text", text=f"系统统计: 用户数={user_count}, 事项数={item_count}")]
        finally:
            db.close()
            
    elif name == "search_items":
        keyword = arguments.get("keyword")
        if not keyword:
            return [types.TextContent(type="text", text="请输入关键词")]
            
        db = SessionLocal()
        try:
            items = db.query(Item).filter(Item.title.contains(keyword)).all()
            if not items:
                return [types.TextContent(type="text", text="未找到相关事项")]
            
            results = []
            for item in items:
                feedback_count = db.query(Feedback).join(ItemUser).filter(ItemUser.item_id == item.id).count()
                results.append(f"ID: {item.id} | 标题: {item.title} | 状态: {item.status} | 反馈数: {feedback_count}")
            
            return [types.TextContent(type="text", text="\n".join(results))]
        finally:
            db.close()
            
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # 运行 stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="feedback-system",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())