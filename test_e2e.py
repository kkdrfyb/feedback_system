import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def test_e2e():
    print("开始 E2E 流程测试...")
    
    try:
        # 1. 登录
        print("尝试登录 admin...")
        res = requests.post(f"{BASE_URL}/login", json={"username": "admin", "password": "123"})
        if res.status_code != 200:
            print(f"登录失败: {res.text}")
            print("请确保后端已启动且数据库中有 admin/123 用户")
            return

        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        admin_id = res.json()["user_id"]
        print("登录成功！")

        # 2. 创建任务
        print("创建一个新任务...")
        import json
        
        # /api/items 接口需要 multipart/form-data
        # 且 deadline 格式为 %Y-%m-%d %H:%M:%S
        
        item_data = {
            "title": "E2E 自动化测试任务",
            "description": "由测试脚本自动创建",
            "deadline": "2025-12-31 23:59:59",
            "must_feedback": True,
            "creator_id": admin_id,
            "user_ids": json.dumps([admin_id]) # JSON 字符串
        }
        
        # 使用 data=... 发送 form-data
        res = requests.post(f"{BASE_URL}/items", data=item_data, headers=headers)
        if res.status_code != 200:
            print(f"任务创建失败: {res.text}")
            return
        item_id = res.json()["id"]
        print(f"任务创建成功, ID: {item_id}")

        # 3. 查看待办
        print("查看待办事项...")
        res = requests.get(f"{BASE_URL}/todos?user_id={admin_id}")
        todos = res.json()
        print(f"当前待办数: {len(todos)}")
        
        # 找到刚刚创建的
        target = next((t for t in todos if t["id"] == item_id), None)
        if not target:
            print("未在待办中找到新任务")
            return
        
        item_user_id = target["item_user_id"]
        print(f"找到待办任务, item_user_id: {item_user_id}")

        # 4. 提交反馈
        print("正在提交反馈...")
        feedback_data = {
            "item_user_id": item_user_id,
            "content": "E2E 测试完成，反馈已提交"
        }
        res = requests.post(f"{BASE_URL}/feedbacks", json=feedback_data)
        if res.status_code == 200:
            print("反馈提交成功！")
        else:
            print(f"反馈提交失败: {res.text}")
            return

        # 5. 再次验证待办已清空
        res = requests.get(f"{BASE_URL}/todos?user_id={admin_id}")
        new_todos = res.json()
        if not any(t["id"] == item_id for t in new_todos):
            print("验证成功：待办已移除！")
            print("--- E2E 测试全部通过 ---")
        else:
            print("验证失败：待办仍存在")

    except Exception as e:
        print(f"测试过程中发生异常: {e}")

if __name__ == "__main__":
    test_e2e()
