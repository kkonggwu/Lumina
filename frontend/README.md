# Lumina 前端项目

高校课程管理RAG智能问答系统 - 前端应用

## 技术栈

- Vue 3
- Vue Router 4
- Pinia (状态管理)
- Axios (HTTP请求)
- Vite (构建工具)

## 项目结构

```
frontend/
├── src/
│   ├── api/          # API接口封装
│   │   ├── request.js    # Axios请求封装
│   │   ├── user.js       # 用户相关接口
│   │   └── rag.js        # RAG问答接口
│   ├── stores/       # Pinia状态管理
│   │   └── auth.js       # 用户认证状态
│   ├── router/        # 路由配置
│   │   └── index.js
│   ├── views/        # 页面组件
│   │   ├── Login.vue     # 登录注册页面
│   │   ├── Chat.vue      # 智能问答页面
│   │   └── Users.vue     # 用户管理页面
│   ├── layouts/      # 布局组件
│   │   └── MainLayout.vue # 主布局（侧边栏+内容区）
│   ├── App.vue       # 根组件
│   ├── main.js       # 入口文件
│   └── style.css     # 全局样式
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

## 安装和运行

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

前端应用将在 `http://localhost:3000` 启动

### 3. 构建生产版本

```bash
npm run build
```

## 功能说明

### 1. 登录注册页面
- 支持用户注册（学生/教师/管理员）
- 支持用户登录
- 登录后自动保存JWT令牌
- 注册成功后自动登录并跳转

### 2. 主页布局
- 左侧可爱风格的侧边栏
- 显示当前用户信息
- 根据用户角色显示不同的菜单项
- 学生用户不显示"用户管理"菜单

### 3. 智能问答页面
- 支持两种问答模式：
  - **RAG问答 (SSE)**: 使用RAG技术，流式返回结果
  - **普通问答**: 直接调用大模型，同步返回结果
- 聊天室风格界面
- 用户消息在右侧，AI消息在左侧
- 支持会话管理（session_id）
- 支持课程ID输入（RAG模式）

### 4. 用户管理页面
- 仅管理员和教师可见
- 查看用户列表
- 按用户类型筛选
- 编辑用户信息
- 修改用户密码

## API接口说明

### 用户接口
- `POST /api/users/register/` - 用户注册
- `POST /api/users/login/` - 用户登录
- `GET /api/users/info/` - 获取用户信息
- `GET /api/users/list/` - 获取用户列表
- `PUT /api/users/update/{user_id}/` - 更新用户信息
- `POST /api/users/change-password/` - 修改密码

### RAG问答接口
- `POST /api/rag/chat/` - 普通问答（同步）
- `POST /api/rag/chat_rag` - RAG问答（SSE流式）
- `GET /api/rag/history/` - 获取问答历史

## 注意事项

1. **JWT令牌**: 登录后令牌会自动保存在localStorage中，并在每次请求时自动添加到请求头
2. **路由守卫**: 未登录用户访问受保护页面会自动跳转到登录页
3. **角色权限**: 学生用户无法访问用户管理页面
4. **SSE流式**: RAG问答使用SSE流式返回，需要后端支持Server-Sent Events

## 开发说明

### 代理配置
开发环境下，Vite会自动代理 `/api` 请求到 `http://localhost:8080`，无需配置CORS。

### 状态管理
使用Pinia管理用户认证状态，包括：
- accessToken: JWT访问令牌
- refreshToken: JWT刷新令牌
- userInfo: 用户信息

### 样式风格
采用可爱的渐变风格，主色调为紫色渐变（#667eea 到 #764ba2）

