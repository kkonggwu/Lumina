#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: reporter_agent.py
@Author: kkonggwu
@Date: 2026/1/31
@Version: 1.0
"""
from datetime import datetime
from typing import Optional, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from utils.ai_handler import AIHandler
from utils.logger import get_logger
from utils.prompt_template import AGENT_REPORT_COMMENT_PROMPT, AGENT_REPORT_SUGGESTION_PROMPT

logger = get_logger('reporter_agent')

class ReporterAgent:
    """
    报告者，负责生成和输出报告
    """
    def __init__(self, provider: str = "qwen"):
        self.ai_handler = AIHandler.create_default(provider=provider)
        self.feedback_chain = self._build_feedback_chain()
        self.suggestion_chain = self. _build_suggestion_chain()
        logger.info(f"ReporterAgent 初始化完成")

    def _build_feedback_chain(self):
        """构建综合评语生成链"""
        prompt = PromptTemplate.from_template(AGENT_REPORT_COMMENT_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    def _build_suggestion_chain(self):
        """构建改进建议生成链"""
        prompt = PromptTemplate.from_template(AGENT_REPORT_SUGGESTION_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    async def report(
            self,
            question: str,
            student_answer: str,
            standard_answer: Optional[str],
            score: float,
            max_score: float,
            missing_keypoints: Optional[List] = None,
            redundant_keypoints: Optional[List] = None,
            scoring_history: Optional[List[dict]] = None,
            reference_materials: Optional[List[dict]] = None,
            scoring_details: Optional[dict] = None,
            human_feedback: Optional[str] = None,
    ) -> dict:
        """
        生成最终判题报告，供 CoordinatorAgent 的 _node_report 节点调用
        :param question:
        :param student_answer:
        :param standard_answer:
        :param score:
        :param max_score:
        :param missing_keypoints:
        :param redundant_keypoints:
        :param scoring_history:
        :param reference_materials:
        :param scoring_details:
        :param human_feedback:
        :return:
        """
        missing_keypoints = missing_keypoints or []
        redundant_keypoints = redundant_keypoints or []
        scoring_history = scoring_history or []
        reference_materials = reference_materials or []
        scoring_details = scoring_details or {}

        logger.info(f"开始生成报告，得分={score}/{max_score},"
                    f"缺失关键点={len(missing_keypoints)}个,"
                    f"冗余关键点={len(redundant_keypoints)}个")

        # 1. 纯规则汇总，不使用 LLM
        summary = self._build_summary(score, max_score, scoring_details)
        keypoint_analysis = self._build_keypoint_analysis(
            missing_keypoints, redundant_keypoints, scoring_details
        )
        meta = self._build_meta(scoring_history, human_feedback, reference_materials)
        recommended_documents = self._build_recommended_documents(reference_materials)

        # 2. LLM 生成内容
        # 将列表转为 Prompt 友好的格式
        matching_keypoints_text = self._format_matching_for_prompt(scoring_details)
        missing_keypoints_text = self._format_keypoints_for_prompt(missing_keypoints)
        redundant_keypoints_text = self._format_redundant_for_prompt(redundant_keypoints)
        reference_hint = self._format_reference_hint(reference_materials)

        feedback = await self._generate_feedback(
            question=question,
            student_answer=student_answer,
            score=score,
            max_score=max_score,
            matching_keypoints=matching_keypoints_text,
            missing_keypoints=missing_keypoints_text,
            redundant_keypoints=redundant_keypoints_text
        )

        improvement_suggestions = await self._generate_suggestion(
            question=question,
            missing_keypoints=missing_keypoints_text,
            redundant_keypoints=redundant_keypoints_text,
            reference_hint=reference_hint
        )

        report = {
            "score": score,
            "max_score": max_score,
            "summary": summary,
            "feedback": feedback,
            "keypoint_analysis": keypoint_analysis,
            "improvement_suggestions": improvement_suggestions,
            "meta": meta,
            "recommended_documents": recommended_documents,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info(f"报告生成完成")
        return report

    async def _generate_feedback(
            self,
            question: str,
            student_answer: str,
            score: float,
            max_score: float,
            matching_keypoints: str,
            missing_keypoints: str,
            redundant_keypoints: str
    ) -> str:
        """
        调用 LLM 生成综合评语
        失败则降级为规则拼接的基础评语，保证报告始终有内容
        :param question:
        :param student_answer:
        :param score:
        :param max_score:
        :param matching_keypoints:
        :param missing_keypoints:
        :param redundant_keypoints:
        :return:
        """
        try:
            feedback = await self.feedback_chain.ainvoke({
                "question": question,
                "student_answer": student_answer,
                "score": score,
                "max_score": max_score,
                "matching_keypoints": matching_keypoints,
                "missing_keypoints": missing_keypoints,
                "redundant_keypoints": redundant_keypoints
            })
            logger.info(f"LLM 评语生成成功")
            return feedback.strip()
        except Exception as e:
            logger.warning(f"LLM 评语生成失败，降级为规则文本：{str(e)}")
            return self._fallback_feedback(score, max_score, missing_keypoints)

    async def _generate_suggestion(
            self,
            question: str,
            missing_keypoints: str,
            redundant_keypoints: str,
            reference_hint: str
    ) -> List[str]:
        """
        调用 LLM 生成改进建议列表
        失败时降级为基于缺失关键点的规则建议
        :param question:
        :param missing_keypoints:
        :param redundant_keypoints:
        :param reference_hint:
        :return:
        """
        if missing_keypoints == "（无）" and redundant_keypoints == "（无）":
            logger.info("无缺失和冗余关键点，跳过改进建议生成")
            return ["答题完整，继续努力！"]

        try:
            raw = await self.suggestion_chain.ainvoke({
                "question": question,
                "missing_keypoints": missing_keypoints,
                "redundant_keypoints": redundant_keypoints,
                "reference_hint": reference_hint
            })
            suggestions = self._parse_suggestions(raw)
            logger.info(f"LLM 改进建议生成成功，共 {len(suggestions)} 条")
            return suggestions
        except Exception as e:
            logger.warning(f"LLM 改进建议生成失败，降级为规则建议：{str(e)}")
            return self._fallback_suggestions(missing_keypoints)

    @staticmethod
    def _parse_suggestions(raw: str) -> List[str]:
        """
        解析 LLM 返回的建议 JSON，支持带/不带 markdown 代码块的格式。
        解析失败时抛出异常，由调用方 _generate_suggestions 触发降级逻辑。
        """
        import json, re
        text = raw.strip()

        # 尝试1: 直接解析
        try:
            data = json.loads(text)
            return data.get("suggestions", [])
        except json.JSONDecodeError:
            pass

        # 尝试2: 提取 markdown 代码块
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            data = json.loads(match.group(1).strip())
            return data.get("suggestions", [])

        # 尝试3: 提取第一个 {...}
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            data = json.loads(brace_match.group(0))
            return data.get("suggestions", [])

        raise ValueError(f"无法解析建议 JSON：{text[:200]}")

    @staticmethod
    def _build_summary(score: float, max_score: float, scoring_details: dict) -> dict:
        """
        组装得分摘要区块
        :param self:
        :param score:
        :param max_score:
        :param scoring_details:
        :return:
        """
        percentage = round((score / max_score * 100), 1) if max_score > 0 else 0.0
        breakdown = scoring_details.get("scoring_breakdown", {})
        grade_level = scoring_details.get("grade_level", "")

        if not grade_level:
            if percentage >= 90:
                grade_level = "优秀"
            elif percentage >= 80:
                grade_level = "良好"
            elif percentage >= 60:
                grade_level = "及格"
            else:
                grade_level = "不及格"

        return {
            "score": score,
            "max_score": max_score,
            "grade_level": grade_level,
            "base_score": breakdown.get("base_score", score),
            "redundant_penalty": breakdown.get("redundant_penalty", 0.0)
        }

    @staticmethod
    def _build_keypoint_analysis(missing_keypoints: List, redundant_keypoints: List, scoring_details: dict) -> dict:
        """
        构建关键点分析区块，汇总匹配/缺失/冗余的详情
        :param missing_keypoints:
        :param redundant_keypoints:
        :param scoring_details:
        :return:
        """
        keypoint_analysis = scoring_details.get("keypoint_analysis", {})
        redundant_analysis = scoring_details.get("redundant_analysis", {})

        return {
            "total_standard": keypoint_analysis.get("total_standard", 0),
            "high_match_count": keypoint_analysis.get("high_match", 0),
            "medium_match_count": keypoint_analysis.get("medium_match", 0),
            "missing_count": keypoint_analysis.get("missing_count", len(missing_keypoints)),
            "point_value": keypoint_analysis.get("point_value", 0),
            "missing_keypoints": missing_keypoints,
            "redundant_keypoints": redundant_keypoints,
            "redundant_invalid_count": redundant_analysis.get("invalid_count", 0),
            "redundant_valid_count": redundant_analysis.get("valid_count", 0)
        }

    @staticmethod
    def _build_meta(scoring_history: List[dict], human_feedback: Optional[str], reference_materials: List[dict]) -> dict:
        """
        组装流程元信息区块
        记录评分次数、置信度变幻、人工干预情况等，便于审计和回溯
        :param scoring_history:
        :param human_feedback:
        :param reference_materials:
        :return:
        """
        rescore_count = sum(1 for h in scoring_history if h.get("is_rescore", False))
        final_confidence = scoring_history[-1].get("confidence", None) if scoring_history else None

        return {
            "total_attempts": len(scoring_history),
            "rescore_count": rescore_count,
            "final_confidence": final_confidence,
            "has_human_feedback": human_feedback is not None,
            "human_feedback": human_feedback,
            "reference_materials_count": len(reference_materials),
            "scoring_history": scoring_history
        }

    @staticmethod
    def _build_recommended_documents(reference_materials: List[dict], max_items: int = 5) -> List[dict]:
        """
        从参考资料列表中提炼出用于前端展示的推荐文档列表。
        仅保留轻量字段，避免在 Grade 中存过大的内容。
        """
        if not reference_materials:
            return []

        recommended = []
        for material in reference_materials[:max_items]:
            if not isinstance(material, dict):
                continue
            content = material.get("content") or ""
            metadata = material.get("metadata") or {}

            # 提取文档标识与标题（尽量复用已有元数据字段）
            doc_id = metadata.get("doc_id") or metadata.get("id") or metadata.get("document_id")
            title = (
                metadata.get("title")
                or metadata.get("file_name")
                or metadata.get("filename")
                or metadata.get("name")
                or "课程相关文档"
            )

            # 截断内容形成摘要，避免过长
            snippet = ""
            if content:
                snippet = content[:200]
                if len(content) > 200:
                    snippet += "..."

            score = material.get("score", 0.0)

            recommended.append(
                {
                    "id": doc_id,
                    "title": title,
                    "score": round(float(score), 4) if isinstance(score, (int, float)) else 0.0,
                    "snippet": snippet,
                }
            )

        logger.info(f"推荐文档列表构建完成，共 {len(recommended)} 条")
        return recommended

    @staticmethod
    def _format_matching_for_prompt(scoring_details: dict) -> str:
        """从 scoring_details 提取匹配信息，格式化为 Prompt 文本"""
        keypoints = scoring_details.get("keypoint_analysis", {})
        high = keypoints.get("high_match", 0)
        medium = keypoints.get("medium_match", 0)
        total = keypoints.get("total_standard", 0)

        if total == 0:
            return "（无匹配的关键点）"
        parts = []
        if high > 0:
            parts.append(f"高度匹配点={high}个")
        if medium > 0:
            parts.append(f"部分匹配点={medium}个")
        return f"共匹配 {total} 个关键点（{'、'.join(parts)}）"

    @staticmethod
    def _format_keypoints_for_prompt(keypoints: List) -> str:
        """将关键点列表转化为编号文本"""
        if not keypoints:
            return "（无）"
        items = []
        for i, kp in enumerate(keypoints,1):
            if isinstance(kp, dict):
                text = kp.get("point") or kp.get("description") or kp.get("content") or str(kp)
            else:
                text = str(kp)
            items.append(f" {i}. {text}")

        return "\n".join(items)

    @staticmethod
    def _format_redundant_for_prompt(redundant_keypoints: List) -> str:
        """格式化冗余关键点，标注是否有效"""
        if not redundant_keypoints:
            return "（无）"
        items = []
        for i, kp in enumerate(redundant_keypoints, 1):
            if isinstance(kp, dict):
                text = kp.get("point") or kp.get("description") or kp.get("content") or str(kp)
                is_valid = kp.get("is_valid", True)
                tag = "（有效补充）" if is_valid else "（无效/错误）"
            else:
                text = str(kp)
                tag = ""
            items.append(f"  {i}. {text} {tag}")
        return "\n".join(items)

    @staticmethod
    def _format_reference_hint(reference_materials: List[dict]) -> str:
        """提炼参考资料的主题词，作为建议生成的方向提示"""
        if not reference_materials:
            return "（无参考资料）"
        hints = []
        for m in reference_materials[:3]:
            content = m.get("content", "")
            # 只取前 60 字作为主题提示，避免 Prompt 过长
            if content:
                hints.append(content[:60] + ("..." if len(content) > 60 else ""))
        return "\n".join(f"  - {h}" for h in hints) if hints else "（无参考资料）"
    @staticmethod
    def _fallback_feedback(
            score: float,
            max_score: float,
            missing_keypoints: str
    ):
        """LLM 评语生成失败时的兜底文本"""
        percentage = round(score / max_score * 100,1) if max_score > 0 else 0
        if percentage >= 90:
            grade_level = "优秀"
        elif percentage >= 80:
            grade_level = "良好"
        elif percentage >= 60:
            grade_level = "及格"
        else :
            grade_level = "不及格"

        base = f"本题得分 {score}/{max_score}（{percentage}%），评级为【{grade_level}】。"
        if missing_keypoints != "（无）":
            base += "答题存在部分知识点遗漏，建议针对缺失内容进行复习巩固。"
        else:
            base += "答题较为完整，继续保持！"
        return base

    @staticmethod
    def _fallback_suggestions(missing_keypoints: str) -> List[str]:
        """LLM 建议生成失败时的规则兜底建议"""
        if missing_keypoints == "（无）":
            return ["答题完整，继续保持！"]
        return [
            "请重点复习题目涉及的相关知识点。",
            "建议对照标准答案，梳理遗漏的关键概念。",
        ]





