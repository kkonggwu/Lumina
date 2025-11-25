#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: rag_service.py
@Author: kkonggwu
@Date: 2025/11/11
@Version: 1.0
"""
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Tuple
from django.conf import settings
from django.http import StreamingHttpResponse

from utils.ai_handler import AIHandler
from utils.logger import get_logger
from utils.prompt_template import CHAT_PROMPT
from rag.models import QAHistory
from config.config import APIConfig
from utils.rag_module import create_rag_pipeline

logger = get_logger(__name__)
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

        # 初始化RAG管道（不加载静态文档，只初始化检索模块）
        # 文档将通过上传接口动态添加到Milvus
        self.rag = create_rag_pipeline(initialize_with_documents=False)

    async def _get_ai_answer_basic(self, question: str) -> str:
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
        answer = await self.ai_handler.chat_basic(question, prompt_template)
        
        if not answer:
            raise Exception("AI返回结果为空")
        
        return answer

    def chat_sync_basic(
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
                answer = asyncio.run(self._get_ai_answer_basic(question))
            except RuntimeError:
                # 如果asyncio.run()失败（可能因为已有事件循环），使用备用方法
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    answer = loop.run_until_complete(self._get_ai_answer_basic(question))
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

    def chat_using_rag(self,
                       user_id: int,
                       question: str,
                       session_id: Optional[str] = None,
                       course_id: Optional[int] = None,
                       top_k=3,
                       similarity_threshold: Optional[float] = 0.3):
        """
        RAG 问答接口 （SSE传输）
        :param user_id: 用户 id
        :param question: 用户问题
        :param session_id: 会话 id
        :param course_id: 课程 id
        :param top_k: 返回结果数量
        :param similarity_threshold: 相似度阈值，低于此值的文档将被过滤（0-1之间，None表示不过滤，默认0.3）
        :return:
        """

        try:
            if not session_id:
                session_id = str(uuid.uuid4())

            return StreamingHttpResponse(
                self._generate_stream(
                    user_id=user_id,
                    question=question,
                    session_id=session_id,
                    course_id=course_id,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold
                ),
                content_type='text/event-stream'
            )
        except Exception as e:
            error_msg = str(e)
            return False, f"问答失败: {error_msg}", None

    def _generate_stream(
        self, 
        user_id, 
        question, 
        session_id, 
        course_id, 
        filters=None, 
        top_k=3,
        similarity_threshold: Optional[float] = 0.3
    ):
        """
        流式生成回答
        :param user_id: 用户ID
        :param question: 用户问题
        :param session_id: 会话ID
        :param course_id: 课程ID
        :param filters: 元数据过滤器
        :param top_k: 返回结果数量
        :return: SSE格式的流式响应
        """
        try:
            # 构造默认的过滤器（如果未提供）
            if filters is None:
                filters = self._build_default_filters(user_id, session_id, course_id)

            # 记录查询日志
            logger.info(f"用户 {user_id} 开始流式查询: {question[:100]}...")
            
            # 用于标记是否已经发送过检索文档
            documents_sent = False

            # 调用RAG服务的流式方法（使用相似度阈值过滤）
            # 默认使用0.3的相似度阈值，过滤掉不相关的文档
            effective_threshold = similarity_threshold if similarity_threshold is not None else 0.3
            for chunk_data in self.rag.process_query_stream(
                    query=question,
                    filters=filters,
                    top_k=top_k,
                    similarity_threshold=effective_threshold
            ):
                # 添加业务相关字段
                chunk_data.update({
                    "user_id": user_id,
                    "session_id": session_id,
                    "course_id": course_id,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 优化数据传输：只在第一次流式响应中包含检索文档，减少传输数据量
                if chunk_data["status"] == "streaming":
                    # 如果是第一次发送且有检索文档
                    if not documents_sent and "retrieved_documents" in chunk_data and chunk_data["retrieved_documents"]:
                        # 保留检索文档，这是第一次发送
                        documents_sent = True
                    else:
                        # 移除检索文档，减少数据传输
                        if "retrieved_documents" in chunk_data:
                            chunk_data.pop("retrieved_documents")
                # 完成状态时可以重新包含检索文档，便于前端展示完整信息
                elif chunk_data["status"] == "completed":
                    # 确保completed状态包含检索文档
                    if "retrieved_documents" not in chunk_data:
                        chunk_data["retrieved_documents"] = []

                # 转换为Server-Sent Events格式
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"用户 {user_id} 流式生成失败: {str(e)}", exc_info=True)
            # 错误处理
            error_data = {
                "success": False,
                "message": f"流式生成失败: {str(e)}",
                "status": "error",
                "error": str(e),
                "user_id": user_id,
                "session_id": session_id,
                "course_id": course_id,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    # TODO 暂时先使用默认的过滤条件
    def _build_default_filters(self, user_id, session_id, course_id):
        """
        构造默认的元数据过滤器
        根据您的业务需求调整这些字段
        """
        filters = {
            # 基础权限和范围过滤
            "course_id": course_id,
            # "user_id": user_id,

            # 状态过滤（只查询有效的文档）
            # "status": "active",

            # 时间范围过滤（示例：只查询最近一年的文档）
            # "created_at": {
            #     "$gte": "2023-01-01T00:00:00Z",
            #     "$lte": "2024-01-01T00:00:00Z"
            # },

            # 文档类型过滤
            # "document_type": {"$in": ["textbook", "lecture_notes", "qa"]},

            # 权限级别过滤
            # "access_level": {"$lte": self._get_user_access_level(user_id)},
        }

        # 根据会话ID添加会话特定的过滤条件
        # if session_id:
            # filters["session_id"] = session_id

        return filters

    # def _build_advanced_filters(self, user_id, question, course_id, additional_filters=None):
    #     """
    #     高级过滤器构造方法 - 根据问题内容动态调整过滤条件
    #     """
    #     base_filters = self._build_default_filters(user_id, None, course_id)
    #
    #     # 移除session_id，因为高级搜索可能跨会话
    #     if "session_id" in base_filters:
    #         base_filters.pop("session_id")
    #
    #     # 添加动态过滤条件
    #     dynamic_filters = {}
    #
    #     # 根据问题关键词调整过滤条件
    #     question_lower = question.lower()
    #
    #     # 示例：如果问题包含"作业"或"assignment"，优先搜索作业相关文档
    #     if any(keyword in question_lower for keyword in ["作业", "assignment", "homework"]):
    #         dynamic_filters["document_type"] = "assignment"
    #
    #     # 示例：如果问题包含"考试"或"考试"，优先搜索考试相关文档
    #     elif any(keyword in question_lower for keyword in ["考试", "exam", "test"]):
    #         dynamic_filters["document_type"] = "exam"
    #
    #     # 示例：如果问题包含"笔记"或"note"，搜索笔记类文档
    #     elif any(keyword in question_lower for keyword in ["笔记", "note"]):
    #         dynamic_filters["document_type"] = "note"
    #
    #     # 合并过滤器
    #     if additional_filters:
    #         dynamic_filters.update(additional_filters)
    #
    #     return {**base_filters, **dynamic_filters}
    #
    # def _get_user_access_level(self, user_id):
    #     """
    #     获取用户权限级别（示例实现）
    #     """
    #     # 这里应该从数据库或用户服务获取用户权限
    #     # 返回数字，例如：1-普通用户，2-VIP用户，3-管理员
    #     return 1  # 默认返回普通用户权限