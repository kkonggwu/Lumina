#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: report_grader_agent.py
@Description: 课程报告题目专用评分 Agent
              从结构完整性、内容质量、语言表达、创新思考四个维度对课程报告进行评分
              支持长文本自动摘要后评分
@Author: kkonggwu
@Date: 2026/4/30
@Version: 1.0
"""
import json
import logging
import re
from typing import Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from utils.ai_handler import AIHandler
from utils.prompt_template import AGENT_REPORT_GRADING_PROMPT, CONCISE_SUMMARY_PROMPT

logger = logging.getLogger('report_grader_agent')

# 报告内容超过此字数时，先进行摘要再评分
REPORT_SUMMARY_THRESHOLD = 3000


class ReportGraderAgent:
    """
    课程报告评分 Agent。

    评分维度：
        structure（20%）— 结构完整性
        content（40%）  — 内容质量
        writing（20%）  — 语言表达
        innovation（20%）— 创新思考
    """

    def __init__(self, provider: str = "qwen"):
        self.ai_handler = AIHandler.create_default(provider=provider)
        self.grading_chain = self._build_grading_chain()
        self.summary_chain = self._build_summary_chain()

    def _build_grading_chain(self):
        prompt = PromptTemplate.from_template(AGENT_REPORT_GRADING_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    def _build_summary_chain(self):
        """复用已有的摘要 Prompt 对超长报告进行压缩"""
        prompt = PromptTemplate.from_template(CONCISE_SUMMARY_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    async def grade(
        self,
        question: str,
        standard_answer: str,
        student_report: str,
        max_score: float = 100.0,
        grading_rubric: Optional[str] = None,
    ) -> dict:
        """
        对学生提交的课程报告进行评分。

        :param question: 报告题目/要求
        :param standard_answer: 参考标准/评分要求描述
        :param student_report: 学生提交的报告全文
        :param max_score: 该题满分
        :param grading_rubric: 教师自定义评分细则（可为空）
        :return: 标准评分结果字典
        """
        logger.info(f"开始评分课程报告，满分={max_score}，报告长度={len(student_report)} 字")

        if not student_report or not student_report.strip():
            return self._empty_submission_result(max_score, "未提交报告内容")

        # 超长报告先做摘要，避免超出 LLM context 窗口
        report_for_eval = await self._preprocess_report(student_report)

        rubric_text = grading_rubric or "（未提供具体评分细则，请按通用学术报告标准评分）"

        try:
            raw = await self.grading_chain.ainvoke({
                "question": question,
                "standard_answer": standard_answer or "（未提供参考标准）",
                "student_report": report_for_eval,
                "grading_rubric": rubric_text,
                "max_score": max_score,
            })
            result = self._parse_json_response(raw)
            return self._build_result(result, max_score)

        except Exception as e:
            logger.error(f"课程报告评分失败：{str(e)}", exc_info=True)
            return self._error_result(max_score, str(e))

    # ------------------------------------------------------------------
    # 内部处理
    # ------------------------------------------------------------------

    async def _preprocess_report(self, report: str) -> str:
        """
        若报告超过阈值字数，先用摘要链压缩，避免 token 溢出。
        摘要后会注明这是摘要版本，以便 LLM 正确理解评分范围。
        """
        if len(report) <= REPORT_SUMMARY_THRESHOLD:
            return report

        logger.info(
            f"报告长度 {len(report)} 字超过阈值 {REPORT_SUMMARY_THRESHOLD}，"
            f"进行摘要压缩后再评分"
        )
        try:
            summary = await self.summary_chain.ainvoke({"query": report})
            return f"【以下为报告摘要，原文已超出长度限制】\n\n{summary}"
        except Exception as e:
            logger.warning(f"摘要生成失败，使用截断版本：{str(e)}")
            # 降级：直接截断，保留前 3000 字
            return report[:REPORT_SUMMARY_THRESHOLD] + "\n\n...（报告过长，已截断）"

    @staticmethod
    def _build_result(llm_result: dict, max_score: float) -> dict:
        """将 LLM 返回的报告评分结果整理为标准格式"""
        structure = llm_result.get("structure", {})
        content = llm_result.get("content", {})
        writing = llm_result.get("writing", {})
        innovation = llm_result.get("innovation", {})

        st_ratio = float(structure.get("score_ratio", 0))
        co_ratio = float(content.get("score_ratio", 0))
        wr_ratio = float(writing.get("score_ratio", 0))
        in_ratio = float(innovation.get("score_ratio", 0))

        st_score = round(max_score * 0.2 * st_ratio, 2)
        co_score = round(max_score * 0.4 * co_ratio, 2)
        wr_score = round(max_score * 0.2 * wr_ratio, 2)
        in_score = round(max_score * 0.2 * in_ratio, 2)

        llm_score = float(llm_result.get("score", st_score + co_score + wr_score + in_score))
        calc_score = round(st_score + co_score + wr_score + in_score, 2)
        final_score = round(min(llm_score, max_score), 2)

        confidence = float(llm_result.get("confidence", 0.75))
        feedback = llm_result.get("feedback", "")
        suggestions = llm_result.get("suggestions", [])

        details = {
            "type": "report",
            "scoring_breakdown": {
                "structure": {
                    "score": st_score,
                    "ratio": st_ratio,
                    "weight": 0.2,
                    "comment": structure.get("comment", ""),
                    "has_introduction": structure.get("has_introduction", False),
                    "has_body": structure.get("has_body", False),
                    "has_conclusion": structure.get("has_conclusion", False),
                },
                "content": {
                    "score": co_score,
                    "ratio": co_ratio,
                    "weight": 0.4,
                    "comment": content.get("comment", ""),
                    "key_points_covered": content.get("key_points_covered", []),
                    "key_points_missing": content.get("key_points_missing", []),
                },
                "writing": {
                    "score": wr_score,
                    "ratio": wr_ratio,
                    "weight": 0.2,
                    "comment": writing.get("comment", ""),
                },
                "innovation": {
                    "score": in_score,
                    "ratio": in_ratio,
                    "weight": 0.2,
                    "comment": innovation.get("comment", ""),
                },
                "calculated_score": calc_score,
                "final_score": final_score,
                "max_score": max_score,
            },
            "suggestions": suggestions,
            "grade_level": ReportGraderAgent._get_grade_level(final_score, max_score),
        }

        return {
            "score": final_score,
            "max_score": max_score,
            "confidence": confidence,
            "feedback": feedback,
            "details": details,
        }

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """从 LLM 返回文本中解析 JSON，兼容多种格式"""
        if not text or not text.strip():
            raise ValueError("LLM 返回内容为空")

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error(f"JSON 解析失败，原始文本：{text[:500]}")
        raise ValueError(f"无法从 LLM 返回中解析 JSON：{text[:200]}")

    @staticmethod
    def _empty_submission_result(max_score: float, reason: str) -> dict:
        return {
            "score": 0.0,
            "max_score": max_score,
            "confidence": 1.0,
            "feedback": reason,
            "details": {
                "grade_level": "不及格",
                "reason": reason,
            },
        }

    @staticmethod
    def _error_result(max_score: float, error_msg: str) -> dict:
        return {
            "score": 0.0,
            "max_score": max_score,
            "confidence": 0.0,
            "feedback": f"评分过程出现异常，请人工复核。错误信息：{error_msg}",
            "details": {
                "grade_level": "待定",
                "error": error_msg,
            },
        }

    @staticmethod
    def _get_grade_level(score: float, max_score: float) -> str:
        pct = (score / max_score * 100) if max_score > 0 else 0
        if pct >= 90:
            return "优秀"
        elif pct >= 80:
            return "良好"
        elif pct >= 60:
            return "及格"
        else:
            return "不及格"
