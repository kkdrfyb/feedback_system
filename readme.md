# 事项反馈系统（IFMS）

> 当前实现说明（2026-08-07）。推荐在浏览器打开同目录的 `readme.html` 阅读；本文保留为可检索、可版本管理的源文件。

## 1. 系统定位

内部事项收集、多人反馈与跟踪系统。发起人创建事项并分配参与人，参与人提交反馈；管理员可管理用户、组织分组、全局导出和操作日志。

当前实现还提供「Excel 模板上传 → 网页单元格编辑 → Excel 导出」的表格协作能力。

## 2. 技术与运行配置

| 层级 | 当前配置 |
| --- | --- |
| 后端 | Python、FastAPI、SQLAlchemy、Alembic、SQLite |
| 前端 | Vue 3、Vite、Element Plus、Axios |
| 鉴权 | JWT Bearer Token，默认有效期 60 分钟 |
| 数据库 | `backend/feedback.db` |
| 附件目录 | 项目根目录 `uploads/`，通过 `/uploads/*` 静态访问 |
| 前端开发地址 | `http://localhost:5173` |
| 后端/API 地址 | `http://127.0.0.1:8000` / `http://127.0.0.1:8000/docs` |

生产环境必须设置 `JWT_SECRET_KEY`；未设置时会使用仅适合本地开发的默认密钥。

## 3. 已实现能力

- 登录与用户管理：管理员创建、删除、导出用户；密码以 bcrypt 哈希保存。
- 事项：创建、附件上传、参与人分配、列表筛选/分页/排序、详情、修改、删除、CSV 导出。
- 反馈：个人待办、提交和修改反馈；全部参与人完成后事项自动标记为 `finished`。
- 分组：个人自定义分组、组织分组同步、CSV 导入用户与分组。
- 统计：事项数、反馈数、完成率、近期事项对比、部门响应率。
- 表格协作：上传 `.xlsx`（最多 10 MB / 200 行）、单元格自动保存、导出 `.xlsx`。
- 运维：Alembic 迁移、数据健康检查、离线打包/安装脚本、定时输出截止前 24 小时未反馈提醒。

## 4. 角色与权限（服务端实际规则）

| 角色 | 主要权限 |
| --- | --- |
| `admin` | 用户、日志、全量事项/统计/导出；可代他人创建事项或提交反馈；可管理所有分组与表格。 |
| `creator` / `feedbacker` | 可创建本人事项、选择参与人；仅查看本人发起或参与的事项，只能修改/删除本人创建的事项，提交/修改本人的反馈；可创建和维护本人非组织分组。 |

所有已登录用户均可打开「新建事项」和「分组管理」。个人分组只向创建者和管理员展示；管理员界面会将这类分组默认折叠在「用户分组」中。协作表格面向所有已登录用户开放查看与导出。

## 5. 本地启动

```bash
# Python 依赖（推荐在 Python 3.11+ 虚拟环境中）
pip install -r requirements.txt

# 数据库迁移
cd backend
alembic -c alembic.ini upgrade head
cd ..

# 启动后端（从项目根目录）
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 另一终端启动前端
cd frontend
npm install
npm run dev
```

空库可运行 `python backend/init_users.py` 生成演示账号和用户；该脚本会创建默认 `admin / 123`，只应在本地演示环境使用，首次使用后应立即改密或改用 CSV 导入账号。

## 6. 验证与部署

```bash
pytest -q
cd frontend && npm run build
```

离线部署可在联网机器运行 `scripts/prepare_offline_bundle.ps1`，离线机器运行 `scripts/install_offline.ps1`；构建后的 `frontend/dist` 会由 FastAPI 托管。

## 7. 文档入口

- `readme.html`：可视化项目说明。
- `事项反馈系统_最终需求文档.html`：以当前实现为基线的需求、差异与问题清单。
