#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: coordinator_agent.py
@Author: kkonggwu
@Date: 2026/1/31
@Version: 1.0
"""
import operator
from datetime import datetime
from typing import TypedDict, Optional, Literal, Annotated, Dict

from langgraph.constants import END
from langgraph.graph import StateGraph

from agent.analyzer_agent import AnalyzerAgent
from agent.reporter_agent import ReporterAgent
from agent.retriever_agent import RetrieverAgent
from agent.scorer_agent import ScorerAgent
from utils.logger import get_logger

logger = get_logger('coordinator_agent')
class ScoringState(TypedDict):
    # 输入信息
    question: str
    student_answer: str
    course_id: int
    question_id: int
    assignment_id: int

    # 检索阶段的结果 (retrieve)
    standard_answer: Optional[str]
    reference_materials: Optional[list]
    # 标准答案的缓存关键点（由 RetrieverAgent 从 DB 取出，教师预分析后存入）
    answer_keypoints: Optional[list]

    # 分析阶段结果 (analyzer)
    student_keypoints: Optional[list]
    missing_keypoints: Optional[list]
    redundant_keypoints: Optional[list]

    # 评分阶段结果 (score)
    score: Optional[float]
    max_score: Optional[float]
    scoring_details: Optional[dict]

    # 生成报告阶段结果 (report)
    report: Optional[dict]

    status: Literal["pending", "retrieved", "analyzed", "scored", "completed", "error", "reviewing", "reviewed"]
    error_message: Optional[str]

    # 重试次数
    retry_count: int
    # 最大重试次数
    max_retries: int
    # 分析重试次数
    analyze_retry_count: int
    # 最大分析重试次数
    max_analyze_retry_count: int
    # 评分历史
    scoring_history: Annotated[list, operator.add]
    # 人工反馈
    human_feedback: Optional[str]
    # 是否需要人工反馈
    needs_human_feedback: bool
    # 置信区间
    confidence_score: Optional[float]


class CoordinatorAgent:
    """
    协调者，作为 Agent 系统的头，分配任务与节点
    """
    def __init__(self):
        self.retriever = RetrieverAgent()
        self.analyzer = AnalyzerAgent()
        self.scorer = ScorerAgent()
        self.reporter = ReporterAgent()

        self.graph = self._bulid_graph()
        self.compiled_graph = self.graph.compile()
        logger.info("Coordinator Agent compiled successfully")


    def _bulid_graph(self) -> StateGraph:
        workflow = StateGraph(ScoringState)

        # 定义节点
        workflow.add_node("retrieve", self._node_retrieve)
        workflow.add_node("analyze", self._node_analyze)
        workflow.add_node("score", self._node_score)
        workflow.add_node("quality_check", self._node_quality_check)
        workflow.add_node("human_review", self._node_human_review)
        workflow.add_node("rescore", self._node_rescore)
        workflow.add_node("report", self._node_report)
        workflow.add_node("error_handle", self._node_error_handler)

        # 设置入口
        workflow.set_entry_point("retrieve")

        # 设置边与路由
        workflow.add_conditional_edges(
            "retrieve",
            self._check_retrieve_status,
            {
                "continue": "analyze",
                "error": "error_handle"
            }
        )

        workflow.add_conditional_edges(
            "analyze",
            self._check_analyze_status,
            {
                "continue": "score",
                "retry": "analyze",
                "error": "error_handle"
            }
        )

        workflow.add_edge("score", "quality_check")

        # 质量检查，检查生成的评分质量是否合格
        # 合格 -> 生成报告
        # 不合格 -> 重新评分
        # 特殊情况 -> 扔审核
        workflow.add_conditional_edges(
            "quality_check",
            self._route_after_quality_check,
            {
                "report": "report",
                "rescore": "rescore",
                "human_review": "human_review",
                "error": "error_handle",
            }
        )

        workflow.add_edge("rescore","quality_check")

        # 人工审核
        # 1. 重新评分
        # 2. 审核通过，生成结果
        # 3. 重新分析
        workflow.add_conditional_edges(
            "human_review",
            self._route_after_human_review,
            {
                "rescore": "rescore",
                "report": "report",
                "analyze": "analyze"
            }
        )

        workflow.add_edge("report", END)
        workflow.add_edge("error_handle", END)

        return workflow


    async def _node_retrieve(self, state: ScoringState) -> Dict:
        """
        检索节点
        1. 从 DB 获取标准答案 + 缓存的关键点（通过 assignment_id + question_id）
        2. （可选）从 Milvus 检索课程文档作为补充参考
        :param state:
        :return:
        """
        logger.info(f"开始检索题目:{state['question_id']}相关资料 (作业ID:{state['assignment_id']})")
        try:
            # 使用 retriever agent 检索相关资料
            result = await self.retriever.retrieve(
                assignment_id=state['assignment_id'],
                question_id=state['question_id'],
                course_id=state['course_id'],
                question=state['question']
            )
            logger.info(
                f"检索完成：标准答案{'已获取' if result.get('standard_answer') else '未获取'}，"
                f"缓存关键点 {len(result.get('answer_keypoints', []))} 个，"
                f"参考资料 {len(result.get('materials', []))} 条"
            )

            return {
                "standard_answer": result.get("standard_answer"),
                "answer_keypoints": result.get("answer_keypoints", []),
                "reference_materials": result.get("materials", []),
                "status": "retrieved"
            }
        except Exception as e:
            logger.error(f"检索失败：{str(e)}")
            return {
                "error_message": f"检索阶段失败:{str(e)}",
                "status": "error"
            }

    async def _node_analyze(self, state: ScoringState) -> Dict:
        """
        分析节点
        1. 检查是否已有缓存的标准答案关键点（由 RetrieverAgent 从 DB 取出）
        2. 如果没有，先调用 analyze_standard_answer 临时生成
        3. 调用 analyze_student_answer 提取学生关键点并与标准关键点对比
        :param state:
        :return:
        """
        logger.info(f"开始分析题目:{state['question_id']}")
        try:
            # 获取标准答案关键点（优先使用 RetrieverAgent 提供的缓存）
            standard_keypoints = state.get("answer_keypoints") or []

            # 如果没有缓存的关键点，临时分析标准答案生成
            if not standard_keypoints:
                logger.info("未找到缓存的标准答案关键点，临时分析生成")
                std_result = await self.analyzer.analyze_standard_answer(
                    question=state['question'],
                    standard_answer=state['standard_answer']
                )
                standard_keypoints = std_result.get("keypoints", [])

            # 调用场景B：分析学生答案 + 与标准关键点对比
            result = await self.analyzer.analyze_student_answer(
                question=state['question'],
                student_answer=state['student_answer'],
                standard_keypoints=standard_keypoints,
                reference_materials=state.get('reference_materials')
            )

            logger.info(
                f"分析完成：标准关键点 {len(standard_keypoints)} 个，"
                f"匹配 {len(result.get('matching_keypoints', []))} 个，"
                f"缺失 {len(result.get('missing_keypoints', []))} 个"
            )

            return {
                "answer_keypoints": standard_keypoints,
                "student_keypoints": result.get('student_keypoints', []),
                "missing_keypoints": result.get('missing_keypoints', []),
                "redundant_keypoints": result.get('redundant_keypoints', []),
                "status": "analyzed"
            }
        except Exception as e:
            logger.error(f"分析失败：{str(e)}")
            return {
                "error_message": f"分析阶段失败:{str(e)}",
                "status": "error"
            }

    async def _node_score(self, state: ScoringState) -> Dict:
        """
        评分节点
        :param state:
        :return:
        """
        attempt = state.get("retry_count",0) + 1
        logger.info(f"开始第 {attempt} 次评分")

        try:
            result = await self.scorer.score(
                max_score=state["max_score"],
                missing_points=state["missing_keypoints"],
                redundant_points=state["redundant_keypoints"],
                student_keypoints=state["student_keypoints"],
                standard_keypoints=state["answer_keypoints"]
            )

            score = result.get("score", 0)
            confidence = result.get("confidence", 0.5)

            logger.info(f"评分完成，得分: {score}/{state['max_score']}, 置信度为：{confidence}")

            scoring_history = {
                "attempt": attempt,
                "score": score,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "is_rescore": False
            }

            return {
                "score": score,
                "confidence_score": confidence,
                "details": result.get("details", {}),
                "scoring_history": [scoring_history],
                "status": "scored"
            }
        except Exception as e:
            logger.error(f"评分失败：{str(e)}")
            return {
                "error_message": f"评分阶段失败: {str(e)}",
                "status": "error"
            }

    async def _node_quality_check(self, state: ScoringState) -> Dict:
        """
        质量检测阶段
        :param state:
        :return:
        """
        logger.info("开始质量检测阶段")

        score = state["score"]
        confidence = state.get("confidence_score", 0.5)
        retry_count = state.get("retry_count", 0)
        student_keypoints_count = len(state.get("student_keypoints", []))

        needs_rescore = False
        needs_human = False
        # 质量检测报告
        reasons = []

        # 配置检查规则
        # 1. 置信度过低
        if confidence < 0.6:
            # 置信度低，需要重新评分
            needs_rescore = True
            reasons.append(f"置信度过低：{confidence:.2f} < 0.6")

        # 2. 极端分数检查，分数差距大需要人工审核
        if score < 50 or score > 95:
            needs_human = True
            reasons.append(f"分数较高或较低：{score}")

        # 3. 检查学生采分点
        if student_keypoints_count < 2:
            needs_rescore = True
            reasons.append(f"学生采分点较少：{student_keypoints_count}")
        # 4. (重新评分阶段) 评分波动过大
        history = state.get("scoring_history", [])
        if len(history) > 1:
            prev_score = history[-2]["score"]
            score_diff = abs(score - prev_score)
            if score_diff > 20:
                needs_human = True
                reasons.append(f"评分波动过大(前次:{prev_score},本次:{score},差异：{score_diff}")

        if needs_human:
            logger.warning(f"需要人工审核: {', '.join(reasons)}")
        elif needs_rescore:
            logger.warning(f"需要重新评分: {', '.join(reasons)}")
        else:
            logger.info("质量检测通过")

        return {
            "needs_human_review": needs_human,
            "status": "reviewing" if (needs_rescore or needs_human) else "scored"
        }

    async def _node_human_review(self, state: ScoringState) -> Dict:
        """
        人工审核节点
        :param state:
        :return:
        """
        # TODO 没想好怎么实现，先空着
        pass

    async def _node_rescore(self, state: ScoringState) -> Dict:
        """
        重新评分节点
        :param state:
        :return:
        """
        retry_count = state.get("retry_count", 0) + 1
        max_retries = state.get("max_retries", 3)

        # 超过最大重试次数，直接转入错误处理
        if retry_count >= max_retries:
            logger.warning(f"重新评分已达最大重试次数 ({retry_count}/{max_retries})，停止重试")
            return {
                "retry_count": retry_count,
                "error_message": f"重新评分超过最大重试次数({max_retries})",
                "status": "error"
            }

        logger.info(f"开始第 {retry_count} 次重新评分")
        try:
            previous_scores = [h["score"] for h in state.get("scoring_history", [])]
            result = await self.scorer.score(
                max_score=state["max_score"],
                missing_points=state["missing_keypoints"],
                redundant_points=state["redundant_keypoints"],
                student_keypoints=state["student_keypoints"],
                standard_keypoints=state["answer_keypoints"],
                strict_mode=True,
                previous_scores=previous_scores
            )
            score = result.get("score", 0)
            confidence = result.get("confidence", 0.5)

            logger.info(f"重新评分完成，得分：{score}/{state['max_score']},置信度：{confidence}")

            scoring_record = {
                "attempt": retry_count,
                "score": score,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "details": result.get("details", {}),
                "is_rescore": True
            }

            return {
                "score": score,
                "confidence_score": confidence,
                "scoring_details": result.get("details", {}),
                "scoring_history": [scoring_record],
                "retry_count": retry_count,
                "status": "scored"
            }
        except Exception as e:
            logger.error(f"重新评分失败：{str(e)}")
            return {
                "error_message": f"重新评分失败：{str(e)}",
                "status": "error"
            }

    async def _node_report(self, state: ScoringState) -> Dict:
        """
        生成报告阶段
        :param state:
        :return:
        """
        logger.info("开始生成最终报告")

        try:
            result = await self.reporter.report(
                question = state["question"],
                student_answer = state["student_answer"],
                standard_answer = state["standard_answer"],
                score = state["score"],
                max_score = state["max_score"],
                missing_keypoints = state["missing_keypoints"],
                redundant_keypoints = state["redundant_keypoints"],
                scoring_history = state["scoring_history"],
                reference_materials = state["reference_materials"],
                scoring_details = state["scoring_details"],
                human_feedback = state["human_feedback"],
            )
            logger.info(f"报告生成完毕，最终得分为：{result['score']}/{state['max_score']}")
            return {
                "report": result,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"报告生成失败：{str(e)}")
            return {
                "error_message": f"报告生成失败：{str(e)}",
                "status": "error"
            }

    async def _node_error_handler(self, state: ScoringState) -> Dict:
        """
        错误处理
        :param state:
        :return:
        """
        error_msg = state.get("error_message", "未知错误")
        logger.error(f"判题流程出错：{error_msg}")
        logger.error(f"重试次数: {state.get('retry_count', 0)}")

        # 生成错误报告
        return {
            "report": {
                "error": True,
                "message": error_msg,
                "retry_count": state.get("retry_count", 0),
                "scoring_history": state.get("scoring_history", []),
                "last_status": state.get("status")
            },
            "status": "error"
        }

    def _check_retrieve_status(self, state: ScoringState) -> str:
        """
        路由工具函数：检查检索状态
        :param state:
        status == "retrieved" -> 进入分析阶段
        status == "error" -> 进入错误处理
        :return: 返回路由判断用的字符串
        """
        if state["status"] == "error":
            logger.warning("检索失败，进入错误处理")
            return "error"

        logger.info("检索成功，进入分析阶段")
        return "continue"

    def _check_analyze_status(self, state: ScoringState) -> str:
        """
        路由工具函数：检查分析状态
        :param state:
        :return:
        """
        if state["status"] == "error":
            logger.warning("分析失败，进入错误处理")
            return "error"

        keypoint_count = len(state.get("answer_keypoints", []))
        analyze_retry_count = state.get("analyze_retry_count", 0)
        max_analyze_retry_count = state.get("max_analyze_retry_count", 3)

        if keypoint_count < 3 and analyze_retry_count < max_analyze_retry_count:
            logger.warning(f"关键点过少({keypoint_count} < 3)，重新分析")
            return "retry"

        logger.info("分析成功，进入评分阶段")
        return "continue"

    def _route_after_quality_check(self, state: ScoringState) -> str:
        """
        路由函数：质量检查后的路由决策
        :param state:
        :return:
        """
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        needs_human_feedback = state.get("needs_human_feedback", False)
        status = state.get("status")
        # 1. 如果超过最大重试次数，
        # - 如果需要人工审核，进入人工审核
        # - 否则，进入错误处理
        if retry_count >= max_retries:
            logger.warning(f"已达到最大重试次数: ({retry_count}/{max_retries})")

            if needs_human_feedback:
                logger.info("需要人工审核")
                return "human_review"
            else:
                logger.info("超过最大重试次数且无需人工审核，进入错误处理")
                return "error"

        # 2. 如果需要人工审核，进入人工审核
        if needs_human_feedback:
            logger.info("质量检测出现异常，转入人工审核")
            return "human_review"
        # 3. 如果需要重新评分，进入重新评分
        if status == "reviewing":
            logger.info("质量检测到需要重新评分")
            confidence = state.get("confidence_score", 0)
            if confidence < 0.6:
                logger.info(f"置信度过低: ({confidence:.2f})，需要重新评分")
                return "rescore"
        # 4. 质量合格，进入报告节点
        logger.info(f"质量检测通过，进入报告生成")
        return "report"

    def _route_after_human_review(self, state: ScoringState) -> str:
        """
        路由函数：人工审核后的路由决策
        :param state:
        :return:
        """
        human_feedback = state.get("human_feedback", "")
        logger.info(f"人工审核反馈：{human_feedback}")

        if "重新分析" in human_feedback:
            logger.info("人工审核要求重新分析")
            return "analyze"
        elif "重新评分" in human_feedback:
            logger.info("人工要求重新评分")
            return "rescore"
        else:
            logger.info("人工审核通过，进入报告生成")
            return "report"