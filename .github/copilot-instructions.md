# Lumina AI 编码代理指南

## 项目概述

**Lumina** 是一个高校课程管理系统，集成了 RAG 增强的 AI 问答功能。这是一个全栈应用，结合了 Django REST 后端、Vue 3 前端和大模型集成，用于智能辅导。

**技术栈**：Django 5.2 + DRF + Vue 3 + Vite | LangChain + Milvus + Sentence Transformers | 大模型：DashScope (Qwen)、OpenAI、DeepSeek

---

## 架构设计

### 后端结构 (Django)

```
Lumina/          # Django 项目配置（settings, urls, wsgi）
├── user/        # 用户管理和 JWT 认证（CustomJWTAuthentication）
├── course/      # 课程和选课模型（带邀请码）
├── rag/         # RAG 系统（问答、聊天历史、文档索引）
├── assignment/  # （stub）作业管理
└── agent/       # （开发中）基于 LangGraph 的代理
```

### 核心服务类

- **RAGService** (`rag/services/rag_service.py`)：编排聊天、文档检索、大模型调用
- **CourseService** (`course/services/course_service.py`)：课程 CRUD、选课管理、权限检查
- **AIHandler** (`utils/ai_handler.py`)：AsyncOpenAI 客户端包装 + LangChain 大模型初始化
- **MilvusManager** (`utils/milvus_manager.py`)：向量数据库（Milvus，端口 19530）

### 前端结构 (Vue 3)

```
frontend/src/
├── api/         # 封装的 Axios API 调用（request.js 基础配置）
├── stores/      # Pinia 认证状态管理
├── router/      # Vue Router 路由配置
└── views/       # 页面组件（Chat.vue、CourseDetail.vue 等）
```

### 数据流

1. **用户认证**：登录 → 通过 `/api/users/login/` 获取 JWT token → 存储在 Pinia store
2. **课程上传**：教师上传文档 → 索引到 Milvus（按课程） → 元数据存在 MySQL/PostgreSQL
3. **Q&A 聊天**：用户查询 → 从 Milvus 检索 → 大模型生成 → 流式响应前端
4. **会话管理**：所有聊天记录保存为 QAHistory（按用户/会话）

---

## 核心模式与约定

### 1. API 响应格式

所有接口都返回统一的 JSON 格式：

```python
{
    "success": bool,        # 成功标志
    "message": str,         # 提示信息
    "data": {...}           # 序列化的响应数据
}
```

**参考文件**：[rag/views.py](rag/views.py#L60-L80) 展示了 ChatView 的响应结构。

### 2. JWT 认证机制

- **自定义认证类**：`user.jwt_auth.CustomJWTAuthentication`（包含调试信息）
- **Token 配置**：访问 Token 有效期 15 分钟，刷新 Token 有效期 1 天（见 `Lumina/settings.py`）
- **装饰器**：保护的视图使用 `@permission_classes([IsAuthenticated])`
- **请求头格式**：`Authorization: Bearer <token>`

### 3. 服务层模式

所有业务逻辑都在 `**/services/` 文件中（不在 views 中）。Views 只处理 HTTP：

- `RAGService.chat()` → 处理大模型调用 + Milvus 检索
- `CourseService.create_course()` → 验证、创建课程、生成邀请码
- AIHandler 同时包装原始 AsyncOpenAI 和 LangChain LLM

### 4. Milvus 向量数据库集成

- **初始化**：自动为每门课程/文档集创建 Collection（collection_name = 唯一 ID）
- **嵌入模型**：`all-MiniLM-L6-v2`（384 维，来自 sentence-transformers）
- **文本分块**：1000 字符块，200 字符重叠（见 [utils/rag_module.py](utils/rag_module.py#L32-L36)）
- **检索策略**：top-k=3，rerank_k=60 用于过滤
- **延迟加载**：文档上传时索引，启动时不预加载

### 5. 大模型配置（APIConfig）

提供商配置在 [config/config.py](config/config.py)：

- **Qwen（默认）**：DashScope API，流式输出启用
- **OpenAI / DeepSeek**：通过环境变量配置
- **关键特性**：所有提供商使用 OpenAI 兼容 API（base_url 可配置）

### 6. 错误处理

- **JWT 错误**：返回 401 + 调试信息（auth_header_present、user_type 等）
- **服务异常**：通过 `get_logger()` 记录，传播到 view 错误处理器
- **流式响应**：使用 `StreamingHttpResponse`，每行一个 JSON 块

### 7. 数据库

- **主数据库**：MySQL（存储 user、course、enrollment、qa_history 等表）
- **向量数据库**：Milvus（远程部署，host/port 在 settings 或环境变量中）
- **模型定义**：User、Course、Enrollment、QAHistory（各自的 `models.py`）
- **迁移**：Django ORM 处理架构，手动 SQL 见 [sql/create_table.sql](sql/create_table.sql)

---

## 开发工作流

### 后端设置

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量（创建 .env 文件）
# DASHSCOPE_API_KEY=<你的 Qwen API 密钥>
# MYSQL_PASSWD=<MySQL 密码>

# 执行迁移（如需要）
python manage.py migrate

# 启动开发服务器
python manage.py runserver
```

### 前端设置

```bash
cd frontend
npm install
npm run dev  # Vite 开发服务器，运行在 :5173
npm run build  # 生产构建
```

### API 文档

- **Swagger UI**：`http://localhost:8000/api/docs/`
- **ReDoc**：`http://localhost:8000/api/redoc/`
- **Schema**：使用 drf_spectacular 生成

### 测试

- 单元测试位于 `**/tests.py`（Django 测试框架）
- RAG/LLM 测试：[Test/langgraph_test.py](Test/langgraph_test.py)、[Test/milvus_test.py](Test/milvus_test.py)
- 运行：`python manage.py test <app_name>`

---

## 常见任务

### 添加新的 API 端点

1. 在 `app/views.py` 中创建视图（继承 APIView，使用序列化器）
2. 在 `app/services/app_service.py` 中添加服务方法
3. 在 `app/urls.py` 中注册 URL
4. 在 `app/serializers.py` 中添加序列化器
5. 使用 `@extend_schema` 装饰器文档化（drf_spectacular）

### 集成新的大模型提供商

1. 在 [config/config.py](config/config.py) 的 APIConfig 字典中添加配置
2. 更新 AIHandler 以支持新提供商的 API 格式
3. 使用现有 RAG 管道测试（如果支持 OpenAI 兼容 API，应该能工作）

### 索引课程文档

1. 前端：POST 到 `/api/course/{course_id}/documents/upload/`
2. 后端：CourseService 保存元数据，AIHandler 分块+嵌入，MilvusManager 索引
3. 验证：直接查询 Milvus 或测试 RAG 检索端点

---

## 关键文件参考

| 文件                                                       | 用途                                               |
| ---------------------------------------------------------- | -------------------------------------------------- |
| [Lumina/settings.py](Lumina/settings.py)                   | Django 配置、REST_FRAMEWORK、JWT、Milvus host:port |
| [user/jwt_auth.py](user/jwt_auth.py)                       | 自定义 JWT 认证后端                                |
| [rag/services/rag_service.py](rag/services/rag_service.py) | 主 RAG 编排                                        |
| [utils/ai_handler.py](utils/ai_handler.py)                 | LLM 客户端包装（异步 + 流式）                      |
| [utils/rag_module.py](utils/rag_module.py)                 | RAG 管道工厂（分块、检索、生成）                   |
| [utils/milvus_manager.py](utils/milvus_manager.py)         | 向量数据库 CRUD 操作                               |
| [frontend/src/api/rag.js](frontend/src/api/rag.js)         | 前端 Q&A API 客户端                                |
| [frontend/src/stores/auth.js](frontend/src/stores/auth.js) | Pinia 认证 store（JWT token 管理）                 |

---

## 已知限制 & 待做项

- **Agent 系统** ([agent/retriever_agent.py](agent/retriever_agent.py))：开发中；LangGraph 集成未完成
- **作业模块**：Stub 实现（仅模型，无 views/service）
- **前端认证拦截器**：可能需要增强 token 刷新流程
- **流式聊天**：客户端 Markdown 渲染（marked + DOMPurify）用于安全

---

## 外部依赖

- **LLM APIs**：DashScope (Qwen)、OpenAI、DeepSeek（通过 AsyncOpenAI 下的 httpx 进行异步调用）
- **向量数据库**：Milvus（自托管，默认 localhost:19530）
- **文档处理**：Unstructured（PDF、DOCX、PPT 解析）、PyPDF、python-pptx
- **嵌入**：sentence-transformers（HuggingFace 模型）
