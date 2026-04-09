# Lumina

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

</div>

**Lumina** is an intelligent subjective question scoring system powered by **LangGraph** and **RAG (Retrieval-Augmented Generation)** technology. It helps teachers automatically grade open-ended answers while providing detailed feedback and recommended readings.

🌍 **Language** · [English](README.md) | [简体中文](README.zh-CN.md)

## ✨ Features

- 🤖 **AI-Powered Scoring**: Uses LangGraph agents to evaluate subjective answers intelligently
- 📚 **RAG Enhancement**: Retrieves relevant course materials to improve scoring accuracy
- 📝 **Assignment Management**: Create, distribute, and grade assignments online
- 👨‍🎓 **User System**: Role-based access control for students, teachers, and admins
- 📊 **Analysis Dashboard**: Visualize student performance and scoring trends
- 🔍 **Recommended Readings**: Automatically suggests relevant learning materials
- 💬 **Streaming Interaction**: Real-time AI response streaming for better user experience

## 🛠️ Tech Stack

| Layer | Technologies                          |
|-------|---------------------------------------|
| Backend | Python, LangGraph, LangChain          |
| Frontend | Vue 3, JavaScript                     |
| Database | MySQL, Milvus                         |
| AI/ML | RAG, LLM  |
| API | Django REST Framework, JWT Auth       |

## 📁 Project Structure

```
Lumina/
├── agent/           # LangGraph agent logic for scoring
├── assignment/      # Assignment management module
├── course/          # Course organization
├── rag/             # RAG retrieval and indexing
├── user/            # User authentication & roles
├── sql/             # Database schemas & queries
├── config/          # Configuration files
├── frontend/        # Vue 3 frontend application
├── utils/           # Helper utilities
├── Test/            # Testing suite
└── manage.py        # Django entry point
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+
- (Optional) OpenAI API key or compatible LLM endpoint

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/kkonggwu/Lumina.git
cd Lumina

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start backend server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend
npm install
npm run serve
```

### Environment Variables

Create a `.env` file in the root directory:

```env
LANGCHAIN_TRACING_V2=false
LANGSMITH_API_KEY="..."
LANGSMITH_PROJECT="default" # or any other project name

DASHSCOPE_API_KEY=your_api_key_here
MYSQL_PASSWD=your_password

ENABLE_MILVUS=true
```

## 📖 Usage

1. **Access the application**: Open `http://localhost:5173`(you can make the changes in frontend/vite.config.js)
2. **Create an account**: Register as a teacher or student
3. **Create an assignment**: Add questions with model answers
4. **Grade submissions**: The AI agent will automatically score student answers
5. **Review feedback**: View scores, comments, and recommended readings

## 📖 Agent Workflow

![流程图.png](staticfiles/%E6%B5%81%E7%A8%8B%E5%9B%BE.png)

## Page Display (Temporary - 2026/4/9)

### Teacher Side - Assignment Management

![作业管理图.png](staticfiles/%E4%BD%9C%E4%B8%9A%E7%AE%A1%E7%90%86%E5%9B%BE.png)

### Student Side - Assignment Evaluation

![作业报告1.png](staticfiles/%E4%BD%9C%E4%B8%9A%E6%8A%A5%E5%91%8A1.png)

![作业报告2.png](staticfiles/%E4%BD%9C%E4%B8%9A%E6%8A%A5%E5%91%8A2.png)

_To be continued for now_

ps: "ENDROLL" sounds great