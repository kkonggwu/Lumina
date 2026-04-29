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
from typing import TypedDict, Optional, Literal, Annotated, Dict, List

from asgiref.sync import sync_to_async
from langgraph.constants import END
from langgraph.graph import StateGraph

from agent.analyzer_agent import AnalyzerAgent
from agent.code_grader_agent import CodeGraderAgent
from agent.report_grader_agent import ReportGraderAgent
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
    # 题目类型：essay | short_answer | python | sql | report
    question_type: str
    # 编程题/SQL 题的测试用例（来自 assignment.questions[].test_cases）
    test_cases: Optional[list]

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
    def __init__(self, enable_milvus: bool = None):
        if enable_milvus is None:
            import os
            enable_milvus = os.getenv('ENABLE_MILVUS', 'false').lower() == 'true'

        self.retriever = RetrieverAgent(enable_milvus=enable_milvus)
        self.analyzer = AnalyzerAgent()
        self.scorer = ScorerAgent()
        self.reporter = ReporterAgent()
        self.code_grader = CodeGraderAgent()
        self.report_grader = ReportGraderAgent()

        self.graph = self._bulid_graph()
        self.compiled_graph = self.graph.compile()
        logger.info("Coordinator Agent compiled successfully")


    def _bulid_graph(self) -> StateGraph:
        workflow = StateGraph(ScoringState)

        # 定义节点
        workflow.add_node("retrieve", self._node_retrieve)
        workflow.add_node("route_by_type", self._node_route_by_type)
        workflow.add_node("analyze", self._node_analyze)
        workflow.add_node("score", self._node_score)
        workflow.add_node("quality_check", self._node_quality_check)
        workflow.add_node("human_review", self._node_human_review)
        workflow.add_node("rescore", self._node_rescore)
        workflow.add_node("code_grade", self._node_code_grade)
        workflow.add_node("report_eval", self._node_report_eval)
        workflow.add_node("report", self._node_report)
        workflow.add_node("error_handle", self._node_error_handler)

        # 设置入口
        workflow.set_entry_point("retrieve")

        # 设置边与路由
        workflow.add_conditional_edges(
            "retrieve",
            self._check_retrieve_status,
            {
                "continue": "route_by_type",
                "error": "error_handle"
            }
        )

        # 按题目类型分叉：文本题 → analyze；代码题 → code_grade；报告题 → report_eval
        workflow.add_conditional_edges(
            "route_by_type",
            self._route_by_type_fn,
            {
                "essay_path": "analyze",
                "code_path": "code_grade",
                "report_path": "report_eval",
            }
        )

        # 代码/报告题：CodeGraderAgent / ReportGraderAgent 已经生成了完整的评分报告，
        # 直接走到 END，避免再被 ReporterAgent（针对关键点流程设计）覆盖结果。
        workflow.add_edge("code_grade", END)
        workflow.add_edge("report_eval", END)

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


    # ============================================================
    # 按题目类型路由
    # ============================================================

    @staticmethod
    async def _node_route_by_type(state: ScoringState) -> Dict:
        """
        空路由节点：本身不修改 state，仅作为分叉点。
        实际路由逻辑由 _route_by_type_fn 决定。
        """
        return {}

    @staticmethod
    def _route_by_type_fn(state: ScoringState) -> str:
        """
        根据题目类型决定后续路径：
          essay / short_answer → essay_path（原有关键点流程）
          python / sql         → code_path（代码评分流程）
          report               → report_path（报告评分流程）
        默认走 essay_path，保持向后兼容。
        """
        q_type = state.get("question_type", "essay")
        if q_type in ("python", "sql"):
            logger.info(f"题目类型={q_type}，走代码评分路径")
            return "code_path"
        if q_type == "report":
            logger.info("题目类型=report，走报告评分路径")
            return "report_path"
        logger.info(f"题目类型={q_type}，走文本关键点评分路径")
        return "essay_path"

    # ============================================================
    # 代码评分节点（python / sql）
    # ============================================================

    async def _node_code_grade(self, state: ScoringState) -> Dict:
        """
        代码评分节点：调用 CodeGraderAgent 对 Python / SQL 代码进行评分，
        并将结果直接组装成最终 report 写入 state。
        """
        q_type = state.get("question_type", "python")
        logger.info(f"进入代码评分节点，类型={q_type}，题目ID={state['question_id']}")

        try:
            if q_type == "python":
                result = await self.code_grader.grade_python(
                    question=state["question"],
                    standard_answer=state.get("standard_answer") or "",
                    student_code=state["student_answer"],
                    test_cases=state.get("test_cases"),
                    max_score=state["max_score"],
                )
            else:
                result = await self.code_grader.grade_sql(
                    question=state["question"],
                    standard_answer=state.get("standard_answer") or "",
                    student_sql=state["student_answer"],
                    test_cases=state.get("test_cases"),
                    max_score=state["max_score"],
                )

            score = result.get("score", 0.0)
            confidence = result.get("confidence", 0.75)
            feedback = result.get("feedback", "")
            details = result.get("details", {})
            suggestions = details.get("suggestions", details.get("scoring_breakdown", {}).get("suggestions", []))

            # 组装成与文本路径相同结构的 report，便于后续统一处理
            report = {
                "score": score,
                "max_score": state["max_score"],
                "feedback": feedback,
                "suggestions": suggestions,
                "scoring_details": details,
                "summary": {
                    "score": score,
                    "max_score": state["max_score"],
                    "grade_level": details.get("grade_level", ""),
                    "percentage": round(score / state["max_score"] * 100, 1) if state["max_score"] > 0 else 0,
                },
            }

            logger.info(f"代码评分完成：{score}/{state['max_score']}，置信度={confidence}")

            return {
                "score": score,
                "confidence_score": confidence,
                "scoring_details": details,
                "report": report,
                "status": "completed",
            }

        except Exception as e:
            logger.error(f"代码评分节点异常：{str(e)}", exc_info=True)
            return {
                "error_message": f"代码评分失败：{str(e)}",
                "status": "error",
            }

    # ============================================================
    # 报告评分节点（report）
    # ============================================================

    async def _node_report_eval(self, state: ScoringState) -> Dict:
        """
        课程报告评分节点：调用 ReportGraderAgent 进行多维度评分。
        """
        logger.info(f"进入报告评分节点，题目ID={state['question_id']}")

        try:
            # 从题目元数据中获取教师自定义评分细则（若有）
            grading_rubric = None

            result = await self.report_grader.grade(
                question=state["question"],
                standard_answer=state.get("standard_answer") or "",
                student_report=state["student_answer"],
                max_score=state["max_score"],
                grading_rubric=grading_rubric,
            )

            score = result.get("score", 0.0)
            confidence = result.get("confidence", 0.75)
            feedback = result.get("feedback", "")
            details = result.get("details", {})
            suggestions = details.get("suggestions", [])

            report = {
                "score": score,
                "max_score": state["max_score"],
                "feedback": feedback,
                "suggestions": suggestions,
                "scoring_details": details,
                "summary": {
                    "score": score,
                    "max_score": state["max_score"],
                    "grade_level": details.get("grade_level", ""),
                    "percentage": round(score / state["max_score"] * 100, 1) if state["max_score"] > 0 else 0,
                },
            }

            logger.info(f"报告评分完成：{score}/{state['max_score']}，置信度={confidence}")

            return {
                "score": score,
                "confidence_score": confidence,
                "scoring_details": details,
                "report": report,
                "status": "completed",
            }

        except Exception as e:
            logger.error(f"报告评分节点异常：{str(e)}", exc_info=True)
            return {
                "error_message": f"报告评分失败：{str(e)}",
                "status": "error",
            }

    # ============================================================
    # 原有节点
    # ============================================================

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
                "analyze_retry_count": state.get("analyze_retry_count", 0) + 1,
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
                "scoring_details": result.get("details", {}),
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

        # 2. 极端分数检查（基于得分率），分数差距大需要人工审核
        max_score = state.get("max_score", 100)
        score_percentage = (score / max_score * 100) if max_score > 0 else 0
        if score_percentage < 20 or score_percentage > 95:
            needs_human = True
            reasons.append(f"得分率极端：{score_percentage:.1f}%（{score}/{max_score}）")

        # 3. 检查学生采分点
        if student_keypoints_count < 2:
            needs_rescore = True
            reasons.append(f"学生采分点较少：{student_keypoints_count}")
        # 4. (重新评分阶段) 评分波动过大（基于得分率差异）
        history = state.get("scoring_history", [])
        if len(history) > 1:
            prev_score = history[-2]["score"]
            score_diff_pct = abs(score - prev_score) / max_score * 100 if max_score > 0 else 0
            if score_diff_pct > 20:
                needs_human = True
                reasons.append(f"评分波动过大(前次:{prev_score},本次:{score},差异：{score_diff_pct:.1f}%)")

        if needs_human:
            logger.warning(f"需要人工审核: {', '.join(reasons)}")
        elif needs_rescore:
            logger.warning(f"需要重新评分: {', '.join(reasons)}")
        else:
            logger.info("质量检测通过")

        return {
            "needs_human_feedback": needs_human,
            "status": "reviewing" if (needs_rescore or needs_human) else "scored"
        }

    async def _node_human_review(self, state: ScoringState) -> Dict:
        """
        人工审核节点
        TODO: 后续对接真正的人工审核机制（如 WebSocket 通知 + 等待教师操作）
        当前默认行为：自动通过，直接进入报告生成
        :param state:
        :return:
        """
        logger.info("进入人工审核节点（当前为自动通过模式）")
        return {
            "human_feedback": "自动通过",
            "status": "reviewed",
        }

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
                scoring_history = state.get("scoring_history", []),
                reference_materials = state.get("reference_materials", []),
                scoring_details = state.get("scoring_details", {}),
                human_feedback = state.get("human_feedback"),
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
            logger.info("质量检测到需要重新评分，进入重新评分")
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
        human_feedback = state.get("human_feedback") or ""
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

    # ============================================================
    # 对外入口方法
    # ============================================================

    async def grade(
            self,
            question: str,
            student_answer: str,
            course_id: int,
            question_id: int,
            assignment_id: int,
            max_score: float,
            question_type: str = "essay",
            test_cases: Optional[list] = None,
    ) -> dict:
        """
        单题评分入口，供 Service 层 / API 视图调用
        :param question: 题目内容
        :param student_answer: 学生答案
        :param course_id: 课程 ID
        :param question_id: 题目 ID（Assignment.questions 中的 id）
        :param assignment_id: 作业 ID
        :param max_score: 该题满分
        :param question_type: 题目类型（essay/short_answer/python/sql/report）
        :param test_cases: 测试用例列表（python/sql 题专用）
        :return: 格式化后的评分结果
        """
        logger.info(
            f"开始判题：作业ID={assignment_id}, 题目ID={question_id}, "
            f"类型={question_type}, 满分={max_score}"
        )

        initial_state = self._build_initial_state(
            question=question,
            student_answer=student_answer,
            course_id=course_id,
            question_id=question_id,
            assignment_id=assignment_id,
            max_score=max_score,
            question_type=question_type,
            test_cases=test_cases,
        )

        try:
            final_state = await self.compiled_graph.ainvoke(initial_state)
            result = self._format_result(final_state)
            logger.info(
                f"判题完成：题目ID={question_id}, "
                f"状态={result['status']}, 得分={result.get('score')}/{max_score}"
            )
            return result
        except Exception as e:
            logger.error(f"判题流程异常：{str(e)}")
            return {
                "status": "error",
                "error_message": f"判题流程异常：{str(e)}",
                "score": None,
                "max_score": max_score,
                "report": None,
            }

    async def grade_submission(self, submission_id: int) -> dict:
        """
        批量判题入口：对某次提交中的所有题目进行评分，并将结果持久化
        :param submission_id: 提交记录 ID
        :return: 包含所有题目评分结果的汇总字典
        """
        logger.info(f"开始批量判题：提交ID={submission_id}")

        from course.models import Submission
        try:
            submission = await sync_to_async(
                lambda: Submission.objects.select_related(
                    'assignment', 'assignment__course'
                ).get(id=submission_id, is_deleted=False)
            )()
        except Submission.DoesNotExist:
            logger.error(f"提交记录不存在：ID={submission_id}")
            return {"status": "error", "error_message": f"提交记录不存在：ID={submission_id}"}

        assignment = submission.assignment
        course_id = assignment.course_id
        questions = assignment.questions or []
        raw_answers = submission.answers or {}

        # 兼容 dict 格式 {"qid": "answer"} 和 list 格式 [{"question_id": ..., "answer": ...}]
        if isinstance(raw_answers, dict):
            answer_map = {str(k): v for k, v in raw_answers.items()}
        elif isinstance(raw_answers, list):
            answer_map = {str(a["question_id"]): a.get("answer", "") for a in raw_answers}
        else:
            answer_map = {}

        results = []
        total_score = 0.0

        for q in questions:
            q_id = q.get("id")
            q_content = q.get("content", "")
            q_max_score = float(q.get("score", 0))
            q_type = q.get("question_type", "essay")
            q_test_cases = q.get("test_cases")
            student_answer = answer_map.get(str(q_id), "")

            if not student_answer.strip():
                results.append({
                    "question_id": q_id,
                    "status": "completed",
                    "score": 0.0,
                    "max_score": q_max_score,
                    "report": {
                        "score": 0.0,
                        "max_score": q_max_score,
                        "feedback": "未作答",
                        "summary": {"score": 0.0, "max_score": q_max_score, "grade_level": "不及格"},
                    },
                })
                continue

            result = await self.grade(
                question=q_content,
                student_answer=student_answer,
                course_id=course_id,
                question_id=q_id,
                assignment_id=assignment.id,
                max_score=q_max_score,
                question_type=q_type,
                test_cases=q_test_cases,
            )
            result["question_id"] = q_id
            results.append(result)
            total_score += result.get("score", 0) or 0

        total_score = round(total_score, 2)
        overall_comment = self._build_overall_comment(results, questions)

        await sync_to_async(self._save_grade)(
            submission=submission,
            total_score=total_score,
            grading_rubric=results,
            overall_comment=overall_comment,
        )

        status = "completed" if all(r.get("status") == "completed" for r in results) else "partial"
        logger.info(f"批量判题完成：提交ID={submission_id}, 总分={total_score}, 状态={status}")

        return {
            "submission_id": submission_id,
            "total_score": total_score,
            "question_results": results,
            "overall_comment": overall_comment,
            "status": status,
        }

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _build_initial_state(
            question: str,
            student_answer: str,
            course_id: int,
            question_id: int,
            assignment_id: int,
            max_score: float,
            question_type: str = "essay",
            test_cases: Optional[list] = None,
    ) -> ScoringState:
        """构造 LangGraph 流程的初始 State"""
        return {
            "question": question,
            "student_answer": student_answer,
            "course_id": course_id,
            "question_id": question_id,
            "assignment_id": assignment_id,
            "question_type": question_type,
            "test_cases": test_cases,
            "max_score": max_score,
            "standard_answer": None,
            "reference_materials": None,
            "answer_keypoints": None,
            "student_keypoints": None,
            "missing_keypoints": None,
            "redundant_keypoints": None,
            "score": None,
            "scoring_details": None,
            "report": None,
            "status": "pending",
            "error_message": None,
            "retry_count": 0,
            "max_retries": 3,
            "analyze_retry_count": 0,
            "max_analyze_retry_count": 3,
            "scoring_history": [],
            "human_feedback": None,
            "needs_human_feedback": False,
            "confidence_score": None,
        }

    @staticmethod
    def _format_result(final_state: dict) -> dict:
        """将 LangGraph 最终 State 清洗为对外返回的标准格式"""
        return {
            "status": final_state.get("status", "error"),
            "score": final_state.get("score"),
            "max_score": final_state.get("max_score"),
            "confidence": final_state.get("confidence_score"),
            "report": final_state.get("report"),
            "scoring_details": final_state.get("scoring_details"),
            "scoring_history": final_state.get("scoring_history", []),
            "error_message": final_state.get("error_message"),
        }

    @staticmethod
    def _save_grade(submission, total_score: float, grading_rubric: list, overall_comment: str):
        """将评分结果持久化到 Grade 表，并更新 Submission 状态"""
        from course.models import Grade
        from django.utils import timezone

        Grade.objects.update_or_create(
            submission=submission,
            defaults={
                "grading_rubric": grading_rubric,
                "overall_comment": overall_comment,
                "is_deleted": False,
            }
        )

        submission.total_score = total_score
        submission.submission_status = 2  # 已批改
        submission.graded_at = timezone.now()
        submission.save(update_fields=["total_score", "submission_status", "graded_at", "updated_at"])

    @staticmethod
    def _build_overall_comment(results: List[dict], questions: list) -> str:
        """根据各题评分结果拼接汇总评语"""
        total = len(results)
        completed = sum(1 for r in results if r.get("status") == "completed")
        error_count = sum(1 for r in results if r.get("status") == "error")
        total_score = sum(r.get("score", 0) or 0 for r in results)
        total_max = sum(float(q.get("score", 0)) for q in questions)

        percentage = round(total_score / total_max * 100, 1) if total_max > 0 else 0

        comment = f"本次作业共 {total} 题，AI 评分完成 {completed} 题"
        if error_count:
            comment += f"，{error_count} 题评分异常"
        comment += f"。总分 {round(total_score, 2)}/{round(total_max, 2)}（{percentage}%）。"
        return comment