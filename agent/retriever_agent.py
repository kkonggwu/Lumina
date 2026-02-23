#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: retriever_agent.py
@Author: kkonggwu
@Date: 2026/1/31
@Version: 1.0
"""
from typing import Dict, List

from asgiref.sync import sync_to_async

from utils.logger import get_logger

logger = get_logger('retriever_agent')
class RetrieverAgent:
    """
    检索 Agent
    """
    def __init__(self, enable_milvus: bool = False):
        """
        初始化检索 Agent
        :param enable_milvus:
        """
        self.enable_milvus = enable_milvus
        self._milvus_manager = None

        logger.info(f"RetrieverAgent 初始化完成")


    async def retrieve(self,
                       question: str,
                       course_id: int,
                       question_id: int,
                       assignment_id: int,
                       top_k: int = 3
                       ):
        """
        主检索方法（供coordinator）使用
        :param question:
        :param course_id:
        :param question_id:
        :param assignment_id:
        :param top_k:
        :return:
        """
        logger.info(f"开始检索：作业ID={assignment_id}，题目ID={question_id}，课程ID:{course_id}")

        # 1. 从数据库获得标准答案和缓存的关键点
        db_result = await self._get_question_data(assignment_id, question_id)

        # 2. 从 Milvus 中获取参考资料（可选）
        materials = []
        if self.enable_milvus and question:
            materials = await self._retrieve_from_milvus(question, course_id, top_k)

        result = {
            "standard_answer": db_result.get("standard_answer"),
            "answer_keypoints": db_result.get("answer_keypoints",[]),
            "is_analyzed": db_result.get("is_analyzed", False),
            "materials": materials,
        }

        logger.info(
            f"检索完成：标准答案{'已获取' if result['standard_answer'] else '未获取'}，"
            f"缓存关键点 {len(result['answer_keypoints'])} 个，"
            f"参考资料 {len(result['materials'])} 条"
        )

        return result

    async def _get_question_data(self, assignment_id: int, question_id: int) -> dict:
        """
        从数据库获取指定题目的标准答案和缓存的关键点
        :param assignment_id:
        :param question_id:
        :return:
        """
        try:
            assignment = await self._get_assignment(assignment_id)

            if not assignment:
                logger.warning(f"未找到作业：ID={assignment_id}")
                return self._empty_question_data()

            question = assignment.questions or []
            question_data = None

            for q in question:
                if q.get("id") == question_id:
                    question_data = q
                    break

            if not question_data:
                logger.warning(f"作业 {assignment_id} 中没有找到题目 ID={question_id}")
                return self._empty_question_data()

            standard_answer = question_data.get("standard_answer","")
            answer_keypoints = question_data.get("answer_keypoints",[])
            is_analyzed = question_data.get("analyzed",False)
            logger.info(
                f"题目数据获取成功：标准答案长度={len(standard_answer)}，"
                f"已分析={is_analyzed}，缓存关键点={len(answer_keypoints)} 个"
            )

            return {
                "standard_answer": standard_answer,
                "answer_keypoints": answer_keypoints if is_analyzed else [],
                "is_analyzed": is_analyzed,
                "question_content": question_data.get("content", ""),
                "score": question_data.get("score", 0),
            }

        except Exception as e:
            logger.error(f"获取题目数据失败：{str(e)}")
            return self._empty_question_data()

    @sync_to_async
    def _get_assignment(self, assignment_id: int):
        """
        从数据库查询 Assignment 对象（同步 ORM 调用，用 sync_to_async 包装）
        :param assignment_id: 作业 ID
        :return: Assignment 对象或 None
        """
        from course.models import Assignment

        try:
            return Assignment.objects.get(id=assignment_id, is_deleted=False)
        except Assignment.DoesNotExist:
            return None

    @staticmethod
    def _empty_question_data() -> dict:
        """返回空的题目数据（查询失败时的默认值）"""
        return {
            "standard_answer": None,
            "answer_keypoints": [],
            "is_analyzed": False,
            "question_content": "",
            "score": 0,
        }
    async def _retrieve_from_milvus(self, question: str, course_id: int, top_k: int = 3) -> List[dict]:
        """
        从 Milvus 检索课程相关文档作为补充参考材料
        :param question: 题目内容（用于向量检索）
        :param course_id: 课程 ID（用于 Milvus 过滤表达式）
        :param top_k: 返回数量
        :return: 参考资料列表 [{"content": str, "score": float, "metadata": dict}, ...]
        """
        try:
            milvus = self._get_milvus_manager()
            if not milvus:
                return []

            # 构建 Milvus 过滤表达式，在数据库层面直接按 course_id 过滤
            filter_expr = f'course_id == {course_id}'

            results = await sync_to_async(milvus.search_similar)(
                query=question,
                limit=top_k,
                filter_expr=filter_expr
            )

            # 格式化结果
            materials = []
            for item in results:
                materials.append({
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0),
                    "metadata": item.get("metadata", {})
                })

            logger.info(f"Milvus 检索完成：获得 {len(materials)} 条课程相关参考资料")
            return materials

        except Exception as e:
            logger.warning(f"Milvus 检索失败（不影响主流程）：{str(e)}")
            return []
    def _get_milvus_manager(self):
        """
        延迟初始化 Milvus 管理器（带快速预检，避免长时间阻塞）
        :return: LangChainMilvusManager 实例或 None
        """
        if self._milvus_manager is None:
            try:
                if not self._check_milvus_reachable():
                    logger.warning("Milvus 不可达，跳过向量检索")
                    return None
                from utils.langchain_milvus_manager import LangChainMilvusManager
                self._milvus_manager = LangChainMilvusManager(
                    collection_name="documents",
                    embedding_model="all-MiniLM-L6-v2"
                )
            except Exception as e:
                logger.warning(f"Milvus 管理器初始化失败：{str(e)}")
                return None
        return self._milvus_manager

    @staticmethod
    def _check_milvus_reachable(host: str = "localhost", port: int = 19530, timeout: float = 2.0) -> bool:
        """快速检测 Milvus 端口是否可达，避免进入 LangChainMilvusManager 的 60 秒重试"""
        import socket
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            return False



