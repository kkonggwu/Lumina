# Lumina

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

</div>

**Lumina** 是一个基于 **LangGraph** 和 **RAG** 技术的智能主观题评分系统。它帮助教师自动批改开放性问题的答案，并提供详细的反馈和推荐阅读材料。

🌍 **语言** · [English](README.md) | [简体中文](README.zh-CN.md)

## ✨ 功能特点

- 🤖 **AI 智能评分**：使用 LangGraph Agent 智能评估主观题答案
- 📚 **RAG 增强**：检索相关课程资料，提升评分准确性
- 📝 **作业管理**：在线创建、分发和批改作业
- 👨‍🎓 **用户系统**：支持学生、教师和管理员三种角色的权限控制
- 📊 **分析看板**：可视化学生表现和评分趋势
- 🔍 **推荐阅读**：自动推荐相关的学习材料
- 💬 **流式交互**：实时 AI 响应流式输出，提升用户体验

## 🛠️ 技术栈

| 层级 | 技术                           |
|------|------------------------------|
| 后端 | Python, LangGraph, LangChain |
| 前端 | Vue 3, JavaScript            |
| 数据库 | MySQL , Milvus               |
| AI/机器学习 | RAG, Multi-Agent             |
| API | Django REST Framework        |

## 📁 项目结构

```
Lumina/
├── agent/           # LangGraph Agent 评分逻辑
├── assignment/      # 作业管理模块
├── course/          # 课程组织管理
├── rag/             # RAG 检索与索引
├── user/            # 用户认证与角色管理
├── sql/             # 数据库表结构及查询
├── config/          # 配置文件
├── frontend/        # Vue 3 前端应用
├── utils/           # 工具函数
├── Test/            # 测试用例
└── manage.py        # Django 入口文件
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
-（可选）OpenAI API Key 或兼容的 LLM 接口

### 后端安装

```bash
# 克隆仓库
git clone https://github.com/kkonggwu/Lumina.git
cd Lumina

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows 使用: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 执行数据库迁移
python manage.py migrate

# 启动后端服务
python manage.py runserver
```

### 前端安装

```bash
cd frontend
npm install
npm run serve
```

### 环境变量配置

在项目根目录创建 `.env` 文件：

```env
LANGCHAIN_TRACING_V2=false
LANGSMITH_API_KEY="..."
LANGSMITH_PROJECT="default" # or any other project name

DASHSCOPE_API_KEY=your_api_key_here
MYSQL_PASSWD=your_password

# Milvus 向量数据库（设为 true 则判题时检索课程文档作为补充参考）
ENABLE_MILVUS=true
```

## 📖 使用指南

1. **访问应用**：打开 `http://localhost:5173`(你可以在frontend/vite.config.js中修改)
2. **注册账号**：选择注册为教师或学生
3. **创建作业**：添加题目和参考答案
4. **批改作答**：AI Agent 将自动评分
5. **查看反馈**：获取分数、评语和推荐阅读材料

## 📖 Agent工作流
![流程图.png](staticfiles/%E6%B5%81%E7%A8%8B%E5%9B%BE.png)

## 页面展示（暂时-2026/4/9）
### 教师端作业管理
![作业管理图.png](staticfiles/%E4%BD%9C%E4%B8%9A%E7%AE%A1%E7%90%86%E5%9B%BE.png)

### 学生端作业评价
![作业报告1.png](staticfiles/%E4%BD%9C%E4%B8%9A%E6%8A%A5%E5%91%8A1.png)

![作业报告2.png](staticfiles/%E4%BD%9C%E4%B8%9A%E6%8A%A5%E5%91%8A2.png)

_暂时先写这么多_

ps: "ENDROLL" 很好听