# 运行本项目

本项目包含后端 (FastAPI) 和前端 (Vue 3 + Vite)。请按以下步骤启动：

## 1. 环境要求
- Python 3.9+
- Node.js v16+ 和 npm

## 2. 启动后端 (Backend)
在项目根目录中执行：

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```
后端服务默认运行在 http://127.0.0.1:8000

- 数据库：首次启动会在 backend 目录下自动创建 SQLite 文件 feedback.db
- 初始化用户（可选）：
  - 在 backend 目录执行 `python init_users.py`，会创建管理员 admin/123 并批量生成测试用户
  - 或执行 `python import_users.py users_template.csv` 从 CSV 导入用户

## 3. 启动前端 (Frontend)
在项目根目录中执行：

```bash
cd frontend
npm install
npm run dev
```
前端开发服务器通常运行在 http://localhost:5173（以控制台输出为准）

- 前端会自动请求同主机的后端 API：`http://<你的主机>:8000/api`
- 已开启跨域，支持前后端不同主机/端口的开发联调

## 4. 访问系统
打开浏览器访问前端地址后登录使用。如果数据库为空，可先按“初始化用户”步骤准备账号。

## 5. 测试（可选）
进入 backend 目录运行：

```bash
pytest -q
```
用于验证基础 API 与认证逻辑是否正常。

## 6. 统计口径说明
- 响应率按“已反馈的参与人 / 被分配的参与人”计算
- 为兼容历史数据，反馈状态认可 "done" 与 "completed" 表示“已反馈”
- 数据统计页面展示全局统计；工作台页面展示“我发起的任务 / 我参与的任务”
