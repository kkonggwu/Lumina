#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: code_grader_agent.py
@Description: Python 编程题与 SQL 语句题的专用评分 Agent
              使用 LLM 从正确性、逻辑性、规范性/高效性三个维度对代码进行评分
"""
import json
import logging
import re
from typing import Optional, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from utils.ai_handler import AIHandler
from utils.prompt_template import AGENT_PYTHON_GRADING_PROMPT, AGENT_SQL_GRADING_PROMPT

logger = logging.getLogger('code_grader_agent')


class CodeGraderAgent:
    """
    代码评分 Agent，负责对 Python 编程题和 SQL 语句题进行评分。

    Python 评分维度：
        correctness（50%）、logic（30%）、style（20%）

    SQL 评分维度：
        correctness（60%）、logic（30%）、efficiency（10%）
    """

    def __init__(self, provider: str = "qwen"):
        self.ai_handler = AIHandler.create_default(provider=provider)
        self.python_chain = self._build_python_chain()
        self.sql_chain = self._build_sql_chain()

    def _build_python_chain(self):
        prompt = PromptTemplate.from_template(AGENT_PYTHON_GRADING_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    def _build_sql_chain(self):
        prompt = PromptTemplate.from_template(AGENT_SQL_GRADING_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    async def grade_python(
        self,
        question: str,
        standard_answer: str,
        student_code: str,
        test_cases: Optional[List] = None,
        max_score: float = 10.0,
    ) -> dict:
        """
        对学生提交的 Python 代码进行评分。

        :param question: 题目描述
        :param standard_answer: 标准答案/参考实现
        :param student_code: 学生提交的代码
        :param test_cases: 测试用例列表
        :param max_score: 该题满分
        :return: 标准评分结果字典
        """
        logger.info(f"开始评分 Python 代码，满分={max_score}")

        if not student_code or not student_code.strip():
            return self._empty_submission_result(max_score, "未提交代码")

        test_cases_text = self._format_test_cases(test_cases)

        try:
            raw = await self.python_chain.ainvoke({
                "question": question,
                "standard_answer": standard_answer or "（未提供标准答案）",
                "student_code": student_code,
                "test_cases": test_cases_text,
                "max_score": max_score,
            })
            result = self._parse_json_response(raw)
            return self._build_python_result(result, max_score)

        except Exception as e:
            logger.error(f"Python 代码评分失败：{str(e)}", exc_info=True)
            return self._error_result(max_score, str(e))

    async def grade_sql(
        self,
        question: str,
        standard_answer: str,
        student_sql: str,
        test_cases: Optional[List] = None,
        max_score: float = 10.0,
    ) -> dict:
        """
        对学生提交的 SQL 语句进行评分。

        :param question: 题目描述
        :param standard_answer: 标准答案/参考 SQL
        :param student_sql: 学生提交的 SQL
        :param test_cases: 测试数据/场景列表
        :param max_score: 该题满分
        :return: 标准评分结果字典
        """
        logger.info(f"开始评分 SQL 语句，满分={max_score}")

        if not student_sql or not student_sql.strip():
            return self._empty_submission_result(max_score, "未提交 SQL")

        test_cases_text = self._format_test_cases(test_cases)

        try:
            raw = await self.sql_chain.ainvoke({
                "question": question,
                "standard_answer": standard_answer or "（未提供标准答案）",
                "student_sql": student_sql,
                "test_cases": test_cases_text,
                "max_score": max_score,
            })
            result = self._parse_json_response(raw)
            return self._build_sql_result(result, max_score)

        except Exception as e:
            logger.error(f"SQL 语句评分失败：{str(e)}", exc_info=True)
            return self._error_result(max_score, str(e))

    # ------------------------------------------------------------------
    # 结果构建
    # ------------------------------------------------------------------

    @staticmethod
    def _build_python_result(llm_result: dict, max_score: float) -> dict:
        """将 LLM 返回的 Python 评分结果整理为标准格式"""
        correctness = llm_result.get("correctness", {})
        logic = llm_result.get("logic", {})
        style = llm_result.get("style", {})

        c_ratio = float(correctness.get("score_ratio", 0))
        l_ratio = float(logic.get("score_ratio", 0))
        s_ratio = float(style.get("score_ratio", 0))

        # 按权重计算各维度得分
        c_score = round(max_score * 0.5 * c_ratio, 2)
        l_score = round(max_score * 0.3 * l_ratio, 2)
        s_score = round(max_score * 0.2 * s_ratio, 2)

        # LLM 已计算好的总分（做二次校验，取更保守的值）
        llm_score = float(llm_result.get("score", c_score + l_score + s_score))
        calc_score = round(c_score + l_score + s_score, 2)
        # 以 LLM 结果为主，但不超过满分
        final_score = round(min(llm_score, max_score), 2)

        confidence = float(llm_result.get("confidence", 0.75))
        feedback = llm_result.get("feedback", "")
        suggestions = llm_result.get("suggestions", [])

        details = {
            "type": "python",
            "scoring_breakdown": {
                "correctness": {
                    "score": c_score,
                    "ratio": c_ratio,
                    "weight": 0.5,
                    "comment": correctness.get("comment", ""),
                    "test_case_results": correctness.get("test_case_results", []),
                },
                "logic": {
                    "score": l_score,
                    "ratio": l_ratio,
                    "weight": 0.3,
                    "comment": logic.get("comment", ""),
                },
                "style": {
                    "score": s_score,
                    "ratio": s_ratio,
                    "weight": 0.2,
                    "comment": style.get("comment", ""),
                },
                "calculated_score": calc_score,
                "final_score": final_score,
                "max_score": max_score,
            },
            "suggestions": suggestions,
            "grade_level": CodeGraderAgent._get_grade_level(final_score, max_score),
        }

        return {
            "score": final_score,
            "max_score": max_score,
            "confidence": confidence,
            "feedback": feedback,
            "details": details,
        }

    @staticmethod
    def _build_sql_result(llm_result: dict, max_score: float) -> dict:
        """将 LLM 返回的 SQL 评分结果整理为标准格式"""
        correctness = llm_result.get("correctness", {})
        logic = llm_result.get("logic", {})
        efficiency = llm_result.get("efficiency", {})

        c_ratio = float(correctness.get("score_ratio", 0))
        l_ratio = float(logic.get("score_ratio", 0))
        e_ratio = float(efficiency.get("score_ratio", 1.0))  # 效率默认满分

        c_score = round(max_score * 0.6 * c_ratio, 2)
        l_score = round(max_score * 0.3 * l_ratio, 2)
        e_score = round(max_score * 0.1 * e_ratio, 2)

        llm_score = float(llm_result.get("score", c_score + l_score + e_score))
        calc_score = round(c_score + l_score + e_score, 2)
        final_score = round(min(llm_score, max_score), 2)

        confidence = float(llm_result.get("confidence", 0.8))
        feedback = llm_result.get("feedback", "")
        suggestions = llm_result.get("suggestions", [])

        details = {
            "type": "sql",
            "scoring_breakdown": {
                "correctness": {
                    "score": c_score,
                    "ratio": c_ratio,
                    "weight": 0.6,
                    "comment": correctness.get("comment", ""),
                    "syntax_valid": correctness.get("syntax_valid", True),
                    "test_case_results": correctness.get("test_case_results", []),
                },
                "logic": {
                    "score": l_score,
                    "ratio": l_ratio,
                    "weight": 0.3,
                    "comment": logic.get("comment", ""),
                },
                "efficiency": {
                    "score": e_score,
                    "ratio": e_ratio,
                    "weight": 0.1,
                    "comment": efficiency.get("comment", ""),
                    "issues": efficiency.get("issues", []),
                },
                "calculated_score": calc_score,
                "final_score": final_score,
                "max_score": max_score,
            },
            "suggestions": suggestions,
            "grade_level": CodeGraderAgent._get_grade_level(final_score, max_score),
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
    def _format_test_cases(test_cases: Optional[List]) -> str:
        """将测试用例列表格式化为 Prompt 中易读的文本"""
        if not test_cases:
            return "（未提供测试用例）"
        lines = []
        for i, tc in enumerate(test_cases, 1):
            if isinstance(tc, dict):
                inp = tc.get("input", tc.get("in", ""))
                out = tc.get("output", tc.get("expected", tc.get("out", "")))
                desc = tc.get("description", tc.get("desc", ""))
                line = f"  用例{i}：输入={inp}，期望输出={out}"
                if desc:
                    line += f"，说明：{desc}"
            else:
                line = f"  用例{i}：{tc}"
            lines.append(line)
        return "\n".join(lines)

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
        """未提交内容时的默认结果"""
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
        """评分异常时的兜底结果"""
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
        """根据得分率返回等级"""
        pct = (score / max_score * 100) if max_score > 0 else 0
        if pct >= 90:
            return "优秀"
        elif pct >= 80:
            return "良好"
        elif pct >= 60:
            return "及格"
        else:
            return "不及格"
