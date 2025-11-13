#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: rag_service.py
@Author: kkonggwu
@Date: 2025/11/11
@Version: 1.0
"""
import uuid
import asyncio
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from utils.ai_handler import AIHandler
from utils.prompt_template import CHAT_PROMPT
from rag.models import QAHistory
from Lumina.config.config import APIConfig


class RAGService:
    """
    RAG服务类，提供普通问答和RAG增强问答功能
    """

    def __init__(self):
        """
        初始化RAG服务
        """
        # 从环境变量获取API密钥
        self.api_key = settings.DASHSCOPE_API_KEY
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY未配置，请在环境变量中设置")

        # 获取API配置
        config = APIConfig.get_config("qwen")
        
        # 初始化AI处理器
        self.ai_handler = AIHandler(
            api_key=self.api_key,
            provider="qwen",
            api_base=config["api_base"]
        )

    async def _get_ai_answer(self, question: str) -> str:
        """
        异步获取AI回答（不涉及数据库操作）
        
        Args:
            question: 用户问题
        
        Returns:
            str: AI回答
        """
        # 使用Prompt模板格式化问题
        prompt_template = CHAT_PROMPT
        
        # 调用AI处理器获取回答
        answer = await self.ai_handler.chat(question, prompt_template)
        
        if not answer:
            raise Exception("AI返回结果为空")
        
        return answer

    def chat_sync(
        self,
        user_id: int,
        question: str,
        session_id: Optional[str] = None,
        course_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[QAHistory]]:
        """
        同步版本的普通问答功能（用于Django视图）
        
        Args:
            user_id: 用户ID
            question: 用户问题
            session_id: 会话ID（可选）
            course_id: 课程ID（可选）
        
        Returns:
            tuple: (是否成功, 消息, QAHistory对象)
        """
        try:
            # 生成会话ID（如果未提供）
            if not session_id:
                session_id = str(uuid.uuid4())

            # 在同步上下文中运行异步API调用
            # 创建一个新的事件循环来运行异步代码，避免与Django的事件循环冲突
            try:
                answer = asyncio.run(self._get_ai_answer(question))
            except RuntimeError:
                # 如果asyncio.run()失败（可能因为已有事件循环），使用备用方法
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    answer = loop.run_until_complete(self._get_ai_answer(question))
                finally:
                    loop.close()

            # 在同步上下文中保存数据库记录（避免异步上下文问题）
            qa_history = QAHistory(
                user_id=user_id,
                course_id=course_id,
                session_id=session_id,
                question=question,
                answer=answer,
                context_docs=None,  # 普通问答没有上下文文档
                source_documents=None,  # 普通问答没有来源文档
                is_deleted=QAHistory.NOT_DELETED
            )
            qa_history.save()

            return True, "问答成功", qa_history

        except Exception as e:
            error_msg = str(e)
            return False, f"问答失败: {error_msg}", None

    @staticmethod
    def get_chat_history(
        user_id: int,
        session_id: Optional[str] = None,
        course_id: Optional[int] = None,
        limit: int = 10
    ) -> list:
        """
        获取问答历史记录
        
        Args:
            user_id: 用户ID
            session_id: 会话ID（可选，用于筛选特定会话）
            course_id: 课程ID（可选，用于筛选特定课程）
            limit: 返回记录数量限制
        
        Returns:
            list: QAHistory对象列表
        """
        try:
            query = QAHistory.objects.filter(
                user_id=user_id,
                is_deleted=QAHistory.NOT_DELETED
            )

            # 按会话ID筛选
            if session_id:
                query = query.filter(session_id=session_id)

            # 按课程ID筛选
            if course_id:
                query = query.filter(course_id=course_id)

            # 按创建时间倒序排列，限制数量
            history = query.order_by('-created_at')[:limit]

            return list(history)
        except Exception as e:
            return []
