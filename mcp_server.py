from fastmcp import FastMCP
from backend.database import SessionLocal
from backend.models import Item, Feedback, ItemUser, User
import sys
import os

# 将当前目录添加到 sys.path 以确保能导入 backend
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 初始化 MCP Server
mcp = FastMCP("Feedback System")

@mcp.tool()
def get_system_stats() -> str:
    """获取系统当前的统计数据（用户数、事项数）"""
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        item_count = db.query(Item).count()
        return f"系统统计: 用户数={user_count}, 事项数={item_count}"
    finally:
        db.close()

@mcp.tool()
def search_items(keyword: str) -> str:
    """根据关键词搜索事项及其反馈情况"""
    db = SessionLocal()
    try:
        items = db.query(Item).filter(Item.title.contains(keyword)).all()
        if not items:
            return "未找到相关事项"
        
        results = []
        for item in items:
            # 简单起见，这里只统计反馈数量
            feedback_count = db.query(Feedback).join(ItemUser).filter(ItemUser.item_id == item.id).count()
            results.append(f"ID: {item.id} | 标题: {item.title} | 状态: {item.status} | 反馈数: {feedback_count}")
        return "\n".join(results)
    finally:
        db.close()

if __name__ == "__main__":
    mcp.run()
