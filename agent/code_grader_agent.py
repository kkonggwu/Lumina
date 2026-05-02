#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: code_grader_agent.py
@Description: Python 编程题与 SQL 语句题的专用评分 Agent
              使用 LLM 从正确性、逻辑性、规范性/高效性三个维度对代码进行评分
@Author: kkonggwu
@Date: 2026/4/30
@Version: 1.0
"""
import json
import logging
import re
from typing import Optional, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from sandbox.service import SandboxService
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
        self.python_weights = {"test": 0.7, "llm": 0.3}
        self.sql_weights = {"test": 0.75, "llm": 0.25}

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

        sandbox_result = SandboxService.run_python(student_code, test_cases)
        test_cases_text = self._format_test_cases(test_cases, sandbox_result)

        try:
            raw = await self.python_chain.ainvoke({
                "question": question,
                "standard_answer": standard_answer or "（未提供标准答案）",
                "student_code": student_code,
                "test_cases": test_cases_text,
                "max_score": max_score,
            })
            result = self._parse_json_response(raw)
            return self._build_python_result(result, max_score, sandbox_result)

        except Exception as e:
            logger.error(f"Python 代码评分失败：{str(e)}", exc_info=True)
            return self._sandbox_only_result(
                question_type="python",
                max_score=max_score,
                sandbox_result=sandbox_result,
                weights=self.python_weights,
                error_msg=str(e),
            )

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

        sandbox_result = SandboxService.run_sql(student_sql, test_cases)
        test_cases_text = self._format_test_cases(test_cases, sandbox_result)

        try:
            raw = await self.sql_chain.ainvoke({
                "question": question,
                "standard_answer": standard_answer or "（未提供标准答案）",
                "student_sql": student_sql,
                "test_cases": test_cases_text,
                "max_score": max_score,
            })
            result = self._parse_json_response(raw)
            return self._build_sql_result(result, max_score, sandbox_result)

        except Exception as e:
            logger.error(f"SQL 语句评分失败：{str(e)}", exc_info=True)
            return self._sandbox_only_result(
                question_type="sql",
                max_score=max_score,
                sandbox_result=sandbox_result,
                weights=self.sql_weights,
                error_msg=str(e),
            )

    # ------------------------------------------------------------------
    # 结果构建
    # ------------------------------------------------------------------

    def _build_python_result(self, llm_result: dict, max_score: float, sandbox_result: dict) -> dict:
        """将 LLM 返回的 Python 评分结果整理为标准格式"""
        correctness = llm_result.get("correctness", {})
        logic = llm_result.get("logic", {})
        style = llm_result.get("style", {})

        c_ratio = float(correctness.get("score_ratio", 0))
        l_ratio = float(logic.get("score_ratio", 0))
        s_ratio = float(style.get("score_ratio", 0))

        pass_rate = float(sandbox_result.get("pass_rate", 0))
        weights = self.python_weights
        llm_ratio = CodeGraderAgent._llm_ratio(llm_result, max_score, fallback=(c_ratio * 0.5 + l_ratio * 0.3 + s_ratio * 0.2))
        final_score, test_score, llm_score = CodeGraderAgent._combine_score(
            max_score=max_score,
            pass_rate=pass_rate,
            llm_ratio=llm_ratio,
            weights=weights,
        )

        l_score = round(max_score * weights["llm"] * 0.6 * l_ratio, 2)
        s_score = round(max_score * weights["llm"] * 0.4 * s_ratio, 2)

        confidence = float(llm_result.get("confidence", 0.75))
        feedback = llm_result.get("feedback", "")
        suggestions = llm_result.get("suggestions", [])
        needs_manual_review = CodeGraderAgent._needs_manual_review(sandbox_result, confidence, pass_rate, llm_ratio)

        details = {
            "type": "python",
            "scoring_mode": "hybrid_test_llm",
            "test_execution": sandbox_result,
            "llm_review": {
                "score_ratio": llm_ratio,
                "raw_score": llm_result.get("score"),
                "confidence": confidence,
            },
            "score_weights": weights,
            "needs_manual_review": needs_manual_review,
            "scoring_breakdown": {
                "correctness": {
                    "score": test_score,
                    "ratio": pass_rate,
                    "weight": weights["test"],
                    "comment": f"沙箱测试通过率 {pass_rate * 100:.1f}%",
                    "test_case_results": sandbox_result.get("case_results", []),
                },
                "logic": {
                    "score": l_score,
                    "ratio": l_ratio,
                    "weight": round(weights["llm"] * 0.6, 2),
                    "comment": logic.get("comment", ""),
                },
                "style": {
                    "score": s_score,
                    "ratio": s_ratio,
                    "weight": round(weights["llm"] * 0.4, 2),
                    "comment": style.get("comment", ""),
                },
                "test_score": test_score,
                "llm_score": llm_score,
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

    def _build_sql_result(self, llm_result: dict, max_score: float, sandbox_result: dict) -> dict:
        """将 LLM 返回的 SQL 评分结果整理为标准格式"""
        correctness = llm_result.get("correctness", {})
        logic = llm_result.get("logic", {})
        efficiency = llm_result.get("efficiency", {})

        c_ratio = float(correctness.get("score_ratio", 0))
        l_ratio = float(logic.get("score_ratio", 0))
        e_ratio = float(efficiency.get("score_ratio", 1.0))  # 效率默认满分

        pass_rate = float(sandbox_result.get("pass_rate", 0))
        weights = self.sql_weights
        llm_ratio = CodeGraderAgent._llm_ratio(llm_result, max_score, fallback=(c_ratio * 0.6 + l_ratio * 0.3 + e_ratio * 0.1))
        final_score, test_score, llm_score = CodeGraderAgent._combine_score(
            max_score=max_score,
            pass_rate=pass_rate,
            llm_ratio=llm_ratio,
            weights=weights,
        )

        l_score = round(max_score * weights["llm"] * 0.7 * l_ratio, 2)
        e_score = round(max_score * weights["llm"] * 0.3 * e_ratio, 2)

        confidence = float(llm_result.get("confidence", 0.8))
        feedback = llm_result.get("feedback", "")
        suggestions = llm_result.get("suggestions", [])
        needs_manual_review = CodeGraderAgent._needs_manual_review(sandbox_result, confidence, pass_rate, llm_ratio)

        details = {
            "type": "sql",
            "scoring_mode": "hybrid_test_llm",
            "test_execution": sandbox_result,
            "llm_review": {
                "score_ratio": llm_ratio,
                "raw_score": llm_result.get("score"),
                "confidence": confidence,
            },
            "score_weights": weights,
            "needs_manual_review": needs_manual_review,
            "scoring_breakdown": {
                "correctness": {
                    "score": test_score,
                    "ratio": pass_rate,
                    "weight": weights["test"],
                    "comment": f"沙箱测试通过率 {pass_rate * 100:.1f}%",
                    "syntax_valid": correctness.get("syntax_valid", True),
                    "test_case_results": sandbox_result.get("case_results", []),
                },
                "logic": {
                    "score": l_score,
                    "ratio": l_ratio,
                    "weight": round(weights["llm"] * 0.7, 2),
                    "comment": logic.get("comment", ""),
                },
                "efficiency": {
                    "score": e_score,
                    "ratio": e_ratio,
                    "weight": round(weights["llm"] * 0.3, 2),
                    "comment": efficiency.get("comment", ""),
                    "issues": efficiency.get("issues", []),
                },
                "test_score": test_score,
                "llm_score": llm_score,
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
    def _format_test_cases(test_cases: Optional[List], sandbox_result: Optional[dict] = None) -> str:
        """将测试用例列表格式化为 Prompt 中易读的文本"""
        if not test_cases:
            lines = ["（未提供测试用例）"]
        else:
            lines = []
            for i, tc in enumerate(test_cases, 1):
                if isinstance(tc, dict):
                    inp = tc.get("input", tc.get("in", ""))
                    out = tc.get("expected", tc.get("expected_rows", tc.get("output", tc.get("out", ""))))
                    desc = tc.get("description", tc.get("desc", ""))
                    fn = tc.get("function_name")
                    setup_sql = tc.get("setup_sql")
                    line = f"  用例{i}："
                    if fn:
                        line += f"函数={fn}，"
                    if setup_sql:
                        line += f"初始化SQL={setup_sql}，"
                    line += f"输入={inp}，期望={out}"
                    if desc:
                        line += f"，说明：{desc}"
                else:
                    line = f"  用例{i}：{tc}"
                lines.append(line)

        if sandbox_result:
            lines.append("\n沙箱真实执行结果：")
            lines.append(
                f"  通过 {sandbox_result.get('passed_count', 0)}/{sandbox_result.get('total_count', 0)}，"
                f"通过率 {float(sandbox_result.get('pass_rate', 0)) * 100:.1f}%"
            )
            if sandbox_result.get("error"):
                lines.append(f"  沙箱错误：{sandbox_result.get('error')}")
            for i, case in enumerate(sandbox_result.get("case_results", []), 1):
                status = "通过" if case.get("passed") or case.get("pass") else "不通过"
                lines.append(
                    f"  结果{i}：{status}，期望={case.get('expected')}，"
                    f"实际={case.get('actual')}，错误={case.get('error') or '无'}"
                )
        return "\n".join(lines)

    @staticmethod
    def _combine_score(max_score: float, pass_rate: float, llm_ratio: float, weights: dict) -> tuple:
        test_score = round(max_score * weights["test"] * pass_rate, 2)
        llm_score = round(max_score * weights["llm"] * llm_ratio, 2)
        final_score = round(min(max(test_score + llm_score, 0), max_score), 2)
        return final_score, test_score, llm_score

    @staticmethod
    def _llm_ratio(llm_result: dict, max_score: float, fallback: float) -> float:
        try:
            score = float(llm_result.get("score"))
            if max_score > 0:
                return max(0.0, min(score / max_score, 1.0))
        except (TypeError, ValueError):
            pass
        return max(0.0, min(float(fallback), 1.0))

    @staticmethod
    def _needs_manual_review(sandbox_result: dict, confidence: float, pass_rate: float, llm_ratio: float) -> bool:
        if sandbox_result.get("status") in {"error", "timeout"}:
            return True
        if confidence < 0.6:
            return True
        return abs(pass_rate - llm_ratio) >= 0.6

    @staticmethod
    def _sandbox_only_result(
        question_type: str,
        max_score: float,
        sandbox_result: dict,
        weights: dict,
        error_msg: str,
    ) -> dict:
        pass_rate = float(sandbox_result.get("pass_rate", 0))
        final_score, test_score, llm_score = CodeGraderAgent._combine_score(
            max_score=max_score,
            pass_rate=pass_rate,
            llm_ratio=0,
            weights=weights,
        )
        details = {
            "type": question_type,
            "scoring_mode": "hybrid_test_llm",
            "test_execution": sandbox_result,
            "llm_review": {
                "score_ratio": 0,
                "confidence": 0,
                "error": error_msg,
            },
            "score_weights": weights,
            "needs_manual_review": True,
            "scoring_breakdown": {
                "correctness": {
                    "score": test_score,
                    "ratio": pass_rate,
                    "weight": weights["test"],
                    "comment": f"LLM 复核失败，仅按沙箱测试通过率计入客观分。错误：{error_msg}",
                    "test_case_results": sandbox_result.get("case_results", []),
                },
                "logic": {
                    "score": 0.0,
                    "ratio": 0.0,
                    "weight": weights["llm"],
                    "comment": "LLM 复核失败，需人工确认代码质量。",
                },
                "calculated_score": final_score,
                "test_score": test_score,
                "llm_score": llm_score,
                "final_score": final_score,
                "max_score": max_score,
            },
            "grade_level": CodeGraderAgent._get_grade_level(final_score, max_score),
        }
        return {
            "score": final_score,
            "max_score": max_score,
            "confidence": 0.0,
            "feedback": "测试已完成，但 LLM 质量复核失败，请教师人工复核。",
            "details": details,
        }

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
