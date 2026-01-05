# 项目程序文件说明文档

本文档说明 `feedback_system_v1_5` 项目中各核心程序文件的作用与关键更新点。

## 1. 后端 (Backend)

后端基于 FastAPI + SQLAlchemy 构建，负责业务逻辑、数据持久化与 API 提供。

### 核心文件

* **`main.py`**
  * 作用: 后端入口。初始化 FastAPI 应用、挂载路由、配置 CORS、挂载静态文件目录 `/uploads`。

* **`models.py`**
  * 作用: 定义 ORM 模型。包含 `User`、`Item`、`ItemUser`、`Feedback`、`Group`、`OperationLog` 等。
  * 更新: 增加 `created_at` 等时间字段以支持排序；`ItemUser` 记录反馈状态（`pending`/`done`/`completed`）。

* **`schemas.py`**
  * 作用: Pydantic 模型，用于请求/响应的数据校验与序列化。

* **`database.py`**
  * 作用: 配置数据库连接与会话管理。
  * 说明: SQLite 文件位于 `backend/feedback.db`（`sqlite:///.../backend/feedback.db`）。

* **`auth.py`**
  * 作用: 登录认证、密码哈希、Token 生成；提供用户管理相关接口。

* **`scheduler.py`**
  * 作用: APScheduler 定时任务。示例任务会在事项截止前 24 小时输出提醒日志。

### 路由模块 (`backend/routers/`)

* **`routers/items.py`**
  * 作用: 事项创建、查询、详情、统计。
  * 更新:
    * `GET /items` 支持作用域（我发起/我参与/全部）、综合搜索（发起人/参与人、标题、状态、时间范围）、服务端排序与分页，并返回总数 `total`。
    * `GET /items/stats/summary` 返回统计概览；兼容历史反馈状态 `"done"` 与 `"completed"`，避免响应率显示为 0%。
    * `GET /items/{id}` 返回完整参与人列表（含状态与反馈内容/时间）。

* **`routers/feedback.py`**
  * 作用: 处理用户提交反馈；统一写入 `ItemUser.feedback_status="done"`；当所有分配用户完成反馈时，自动将 `Item.status` 更新为 `finished`。

* **`routers/groups.py`**
  * 作用: 分组管理相关接口。

### 测试与工具脚本

* **`backend/tests/`**
  * 作用: 基础接口与认证逻辑的单元测试。

* **`stress_test_simulation.py`**
  * 作用: 压力测试脚本，用于批量构造数据并模拟反馈；反馈状态统一为 `"done"`，与统计口径一致。

* **`init_users.py` / `import_users.py`**
  * 作用: 初始化/导入用户数据。默认创建管理员 `admin/123` 并可批量生成或导入测试用户。

---

## 2. 前端 (Frontend)

前端基于 Vue 3 + Element Plus 构建，负责用户交互与界面展示。

### 核心视图 (`frontend/src/views/`)

* **`Dashboard.vue` (工作台/首页)**
  * 作用: 展示“我发起的任务 / 我参与的任务”；全局统计迁移至数据统计页面。
  * 更新: 作用域切换与综合搜索表单；服务端排序与分页；加载提示优化。

* **`DataStats.vue` (数据统计)**
  * 作用: 展示统计概览与趋势图（管理员全量、普通用户按个人作用域）。
  * 更新: 完全对接后端 `/items/stats/summary`，兼容 `"done"`/`"completed"` 状态的响应率计算。

* **`ItemDetail.vue` (事项详情)**
  * 作用: 显示事项详情与完整参与人反馈列表。

* **`GroupManagement.vue` (用户/分组管理)**
  * 作用: 管理分组与用户；内置新增/删除用户与导出支持。

### 配置文件

* **`frontend/src/api.js`**
  * 作用: Axios 实例配置；基于当前页面主机动态拼接后端基础路径 `http://<host>:8000/api`；支持 Token 拦截。

---

## 3. 根目录文件

* **`readme.md`**
  * 作用: 运行与部署指南。

* **`shuoming.md`**
  * 作用: 本说明文件。
