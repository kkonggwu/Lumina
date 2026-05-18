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
from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.ai_handler import AIHandler
from utils.prompt_template import CONCISE_SUMMARY_PROMPT

logger = logging.getLogger('report_grader_agent')

# 报告内容超过此字数时，先进行摘要再评分
REPORT_SUMMARY_THRESHOLD = 3000
REPORT_CHUNK_SIZE = 800
REPORT_CHUNK_OVERLAP = 150
REPORT_CHUNK_SEPARATORS = ["\n\n", "\n", "。", "；", "！", "？", ".", " ", ""]
MAX_DIMENSION_CONTEXT_LENGTH = 3600

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

    async def aclose(self):
        await self.ai_handler.aclose()

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    async def grade(
        self,
        question: str,
        standard_answer: str,
        student_report: str,
        max_score: float = 100.0,
        grading_rubric: Optional[Any] = None,
        visual_evidence: Optional[Dict[str, Any]] = None,
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

        try:
            rubric = self._normalize_rubric(grading_rubric)
            chunks = self._split_report(student_report)
            dimension_results = []

            for dimension in rubric["dimensions"]:
                selected_chunks = self._select_chunks_for_dimension(chunks, dimension)
                evidence_context = self._format_chunks_for_prompt(selected_chunks)
                visual_context = self._format_visual_evidence_for_prompt(visual_evidence, dimension)
                dimension_result = await self._grade_dimension(
                    question=question,
                    standard_answer=standard_answer,
                    rubric_context=rubric["rubric_context"],
                    dimension=dimension,
                    evidence_context=evidence_context,
                    visual_context=visual_context,
                    max_score=max_score,
                )
                dimension_results.append(dimension_result)

            return self._build_rubric_result(
                dimension_results=dimension_results,
                rubric=rubric,
                max_score=max_score,
                chunk_count=len(chunks),
                visual_evidence=visual_evidence,
            )

        except Exception as e:
            logger.error(f"课程报告评分失败：{str(e)}", exc_info=True)
            return self._error_result(max_score, str(e))

    # ------------------------------------------------------------------
    # 内部处理
    # ------------------------------------------------------------------

    def _normalize_rubric(self, grading_rubric: Optional[Any]) -> dict:
        """将教师评分细则归一化为统一的维度列表。"""
        if isinstance(grading_rubric, dict) and isinstance(grading_rubric.get("dimensions"), list):
            raw_dimensions = grading_rubric["dimensions"]
            total_weight = sum(float(d.get("weight", 0)) for d in raw_dimensions) or 1.0
            divisor = 100.0 if total_weight > 1.5 else 1.0

            dimensions = []
            for index, dim in enumerate(raw_dimensions):
                weight = float(dim.get("weight", 0)) / divisor
                dimensions.append({
                    "id": dim.get("id") or f"dimension_{index + 1}",
                    "name": dim.get("name") or f"评分维度{index + 1}",
                    "weight": weight,
                    "criteria": self._to_text_list(dim.get("criteria")),
                    "required_evidence": self._to_text_list(dim.get("required_evidence")),
                })

            normalized_total = sum(d["weight"] for d in dimensions) or 1.0
            for dim in dimensions:
                dim["weight"] = dim["weight"] / normalized_total

            return {
                "mode": "structured",
                "rubric_context": json.dumps(grading_rubric, ensure_ascii=False),
                "dimensions": dimensions,
            }

        rubric_context = grading_rubric if isinstance(grading_rubric, str) else "（未提供具体评分细则，请按通用学术报告标准评分）"
        return {
            "mode": "default",
            "rubric_context": rubric_context,
            "dimensions": [
                {
                    "id": "structure",
                    "name": "结构完整性",
                    "weight": 0.2,
                    "criteria": ["报告结构完整", "包含引言、正文、结论", "段落组织清晰", "格式与逻辑层次规范"],
                    "required_evidence": ["引言", "正文", "结论", "目录", "章节"],
                },
                {
                    "id": "content",
                    "name": "内容质量",
                    "weight": 0.4,
                    "criteria": ["紧扣题目要求", "覆盖核心任务", "分析充分", "结论有证据支撑", "不存在明显错误"],
                    "required_evidence": ["数据集", "分析", "结果", "结论", "图表"],
                },
                {
                    "id": "writing",
                    "name": "语言表达",
                    "weight": 0.2,
                    "criteria": ["语言通顺", "术语准确", "表达清晰", "学术写作规范"],
                    "required_evidence": ["说明", "分析", "讨论", "参考文献"],
                },
                {
                    "id": "innovation",
                    "name": "创新思考",
                    "weight": 0.2,
                    "criteria": ["具有独立分析", "提出合理思考", "有应用价值或延伸观点"],
                    "required_evidence": ["创新", "改进", "启示", "局限", "展望"],
                },
            ],
        }

    @staticmethod
    def _to_text_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    @staticmethod
    def _split_report(report: str) -> List[str]:
        """用递归字符滑动窗口切分报告，避免单次 LLM 调用处理整篇长文。"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=REPORT_CHUNK_SIZE,
            chunk_overlap=REPORT_CHUNK_OVERLAP,
            separators=REPORT_CHUNK_SEPARATORS,
        )
        docs = splitter.create_documents([report])
        return [doc.page_content for doc in docs if doc.page_content.strip()]

    def _select_chunks_for_dimension(self, chunks: List[str], dimension: Dict[str, Any], limit: int = 4) -> List[Dict[str, Any]]:
        """按评分维度从报告分块中挑选最相关的片段。"""
        if not chunks:
            return []

        keywords = self._extract_keywords(
            " ".join([dimension["name"], *dimension.get("criteria", []), *dimension.get("required_evidence", [])])
        )
        scored_chunks = []
        for index, chunk in enumerate(chunks):
            score = 0
            for keyword in keywords:
                if keyword and keyword in chunk:
                    score += 1
            scored_chunks.append({
                "index": index + 1,
                "content": chunk,
                "score": score,
            })

        ranked = sorted(scored_chunks, key=lambda item: item["score"], reverse=True)
        selected = [item for item in ranked if item["score"] > 0][:limit]
        if not selected:
            selected = scored_chunks[:min(limit, len(scored_chunks))]
        return selected

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """提取用于片段筛选的轻量关键词。"""
        if not text:
            return []
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z_][A-Za-z0-9_]{1,}", text)
        stopwords = {"报告", "评分", "维度", "要求", "是否", "进行", "包含", "给出", "分析", "说明"}
        keywords = []
        for token in tokens:
            token = token.strip()
            if token and token not in stopwords and token not in keywords:
                keywords.append(token)
        return keywords[:30]

    @staticmethod
    def _format_chunks_for_prompt(chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "（未找到可用于该维度评分的报告片段）"

        parts = []
        current_length = 0
        for item in chunks:
            text = item["content"].strip()
            block = f"[片段{item['index']}]\n{text}\n"
            if current_length + len(block) > MAX_DIMENSION_CONTEXT_LENGTH:
                remaining = MAX_DIMENSION_CONTEXT_LENGTH - current_length
                if remaining <= 100:
                    break
                block = block[:remaining] + "\n...(片段已截断)\n"
            parts.append(block)
            current_length += len(block)
            if current_length >= MAX_DIMENSION_CONTEXT_LENGTH:
                break
        return "\n".join(parts)

    async def _grade_dimension(
        self,
        question: str,
        standard_answer: str,
        rubric_context: str,
        dimension: Dict[str, Any],
        evidence_context: str,
        visual_context: str,
        max_score: float,
    ) -> dict:
        """调用 LLM 对单个评分维度评分，并执行基本保护规则。

        说明：不再用 LangChain `PromptTemplate` 的 f-string 渲染，避免学生 / 教师
        自由文本中夹带的字面 `{` `}`（如 JSON 片段）被解析为占位符，
        触发 "Invalid format specifier in f-string template. Nested replacement
        fields are not allowed" 之类的错误。
        """
        try:
            prompt_text = self._render_dimension_prompt(
                question=question,
                standard_answer=standard_answer or "（未提供参考标准）",
                rubric_context=rubric_context,
                dimension=dimension,
                evidence_context=evidence_context,
                visual_context=visual_context,
            )
            raw = await self.ai_handler.get_completion(prompt_text)
            parsed = self._parse_json_response(raw)
        except Exception as e:
            logger.warning(
                f"维度 {dimension['id']} 评分失败，标记人工复核: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            parsed = {
                "score_ratio": 0.0,
                "confidence": 0.0,
                "evidence_quotes": [],
                "missing_requirements": ["模型评分失败，需人工复核"],
                "reason": f"模型评分失败：{str(e)}",
                "suggestions": ["请教师人工检查该评分维度"],
                "requires_manual_review": True,
                "parse_error": str(e),
            }

        evidence_quotes = self._to_text_list(parsed.get("evidence_quotes"))[:3]
        missing_requirements = self._to_text_list(parsed.get("missing_requirements"))
        suggestions = self._to_text_list(parsed.get("suggestions"))
        score_ratio = self._clamp_float(parsed.get("score_ratio"), 0.0, 1.0)
        confidence = self._clamp_float(parsed.get("confidence"), 0.0, 1.0)
        requires_manual_review = bool(parsed.get("requires_manual_review"))

        has_visual_support = visual_context not in (None, "", "（未提供报告附件视觉证据）")
        if not evidence_quotes and not has_visual_support:
            score_ratio = min(score_ratio, 0.4)
            confidence = min(confidence, 0.6)
            requires_manual_review = True
            if "缺少可引用证据" not in missing_requirements:
                missing_requirements.append("缺少可引用证据")

        dimension_score = round(max_score * dimension["weight"] * score_ratio, 2)
        return {
            "id": dimension["id"],
            "name": dimension["name"],
            "weight": dimension["weight"],
            "score_ratio": score_ratio,
            "score": dimension_score,
            "max_score": round(max_score * dimension["weight"], 2),
            "confidence": confidence,
            "evidence_quotes": evidence_quotes,
            "missing_requirements": missing_requirements,
            "reason": str(parsed.get("reason", "")).strip(),
            "suggestions": suggestions,
            "requires_manual_review": requires_manual_review,
        }

    @staticmethod
    def _format_list_for_prompt(items: List[str]) -> str:
        if not items:
            return "（无）"
        return "\n".join(f"- {item}" for item in items)

    @classmethod
    def _render_dimension_prompt(
        cls,
        question: str,
        standard_answer: str,
        rubric_context: str,
        dimension: Dict[str, Any],
        evidence_context: str,
        visual_context: str,
    ) -> str:
        """
        手工拼接评分 prompt，避免 LangChain PromptTemplate 的 f-string 解析对
        参数值中的 `{` `}` 做二次校验。任何字段的字面 JSON / 代码片段都能安全注入。
        """
        criteria_text = cls._format_list_for_prompt(dimension.get("criteria", []))
        evidence_text = cls._format_list_for_prompt(dimension.get("required_evidence", []))
        return (
            "你是一位严格、客观的大学课程大作业评阅专家。请只根据提供的报告片段与评分维度进行评分。\n\n"
            "## 作业要求\n"
            f"{question}\n\n"
            "## 参考标准\n"
            f"{standard_answer}\n\n"
            "## 评分细则补充\n"
            f"{rubric_context}\n\n"
            "## 当前评分维度\n"
            f"维度名称：{dimension.get('name', '')}\n"
            f"维度权重：{dimension.get('weight', 0)}\n"
            "评分标准：\n"
            f"{criteria_text}\n"
            "必须寻找的证据：\n"
            f"{evidence_text}\n\n"
            "## 可用报告片段\n"
            f"{evidence_context}\n\n"
            "## 视觉证据（来自报告附件的图表/页面识别）\n"
            f"{visual_context}\n\n"
            "## 评分规则\n"
            "1. 只能依据“可用报告片段”和“视觉证据”评分，不要臆测报告未提供的内容。\n"
            "2. 若两者都没有支撑该维度的证据，score_ratio 最高只能为 0.4。\n"
            "3. evidence_quotes 优先引用报告片段中的原文短句，最多 3 条；可补充对视觉证据的简短描述。\n"
            "4. missing_requirements 写出该维度缺失或证据不足的要求。\n"
            "5. confidence 表示本维度判断可信度，范围 0 到 1。\n"
            "6. 如果证据不足、片段与维度无关、模型难以判断，请将 requires_manual_review 设为 true。\n"
            "7. 评分立场偏宽松：只要文字或图片中能看到对应工作（如出现箱线图、Parzen 窗、PCA 等），就可以给较高比例；不需要严格验证数值正确性。\n\n"
            "## 输出要求\n"
            "必须严格输出合法 JSON，不要输出 Markdown 或额外解释。\n\n"
            "## 输出格式\n"
            "{\n"
            "  \"score_ratio\": 0.75,\n"
            "  \"confidence\": 0.82,\n"
            "  \"evidence_quotes\": [\"报告中的证据短句1\"],\n"
            "  \"missing_requirements\": [\"缺失要求1\"],\n"
            "  \"reason\": \"该维度评分理由\",\n"
            "  \"suggestions\": [\"可执行改进建议1\"],\n"
            "  \"requires_manual_review\": false\n"
            "}\n"
        )

    @staticmethod
    def _format_visual_evidence_for_prompt(
        visual_evidence: Optional[Dict[str, Any]],
        dimension: Dict[str, Any],
    ) -> str:
        """把视觉识别结果格式化成 prompt 友好的多行文本。"""
        if not visual_evidence:
            return "（未提供报告附件视觉证据）"

        findings = visual_evidence.get("chart_findings") or []
        charts_detected = visual_evidence.get("charts_detected") or []
        if not findings and not charts_detected:
            return "（报告附件未识别到可用的图表证据）"

        # 维度关键字优先选择相关图，限制条数避免 prompt 过长
        keywords = []
        for source in (dimension.get("name"), *dimension.get("criteria", []), *dimension.get("required_evidence", [])):
            keywords.extend(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]+", str(source or "")))
        keywords = [k for k in keywords if k]

        def score_finding(finding: dict) -> int:
            text_blob = " ".join([
                str(finding.get("analysis_quality_hint", "")),
                " ".join(finding.get("chart_types", [])),
                str(finding.get("kind", "")),
            ])
            return sum(1 for kw in keywords if kw and kw in text_blob)

        ranked = sorted(findings, key=score_finding, reverse=True)[:5]

        lines = [f"概述: {visual_evidence.get('visual_summary', '')}".strip()]
        if charts_detected:
            lines.append(f"检测到的图表类型集合: {', '.join(charts_detected)}")
        for index, finding in enumerate(ranked, 1):
            location = f"页{finding.get('page')}" if finding.get('page') else f"图{finding.get('image_index', index)}"
            chart_types = ', '.join(finding.get('chart_types', [])) or '未明确'
            lines.append(
                f"- 视觉证据{index}（{location}）：包含图表={finding.get('has_chart')}，"
                f"类型=[{chart_types}]，是否概率密度图={finding.get('is_probability_plot')}，"
                f"可读={finding.get('axes_readable')}，置信度={finding.get('confidence')}，"
                f"说明={finding.get('analysis_quality_hint', '')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _clamp_float(value: Any, min_value: float, max_value: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = min_value
        return round(max(min(number, max_value), min_value), 4)

    def _build_rubric_result(
        self,
        dimension_results: List[dict],
        rubric: dict,
        max_score: float,
        chunk_count: int,
        visual_evidence: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """汇总多维度评分结果。"""
        if not dimension_results:
            logger.warning("评分结果为空，整体标记人工复核")
            return self._error_result(max_score, "未生成任何评分维度结果")

        final_score = round(min(sum(item["score"] for item in dimension_results), max_score), 2)
        confidence = round(
            sum(item["confidence"] * item["weight"] for item in dimension_results),
            4,
        )
        if max_score > 0:
            score_ratio = final_score / max_score
            needs_manual_review = (
                confidence < 0.6
                or any(item["requires_manual_review"] for item in dimension_results)
                or score_ratio < 0.2
                or score_ratio > 0.95
            )
        else:
            needs_manual_review = True

        suggestions = self._collect_unique_suggestions(dimension_results)
        feedback = self._build_feedback(final_score, max_score, dimension_results, needs_manual_review)
        scoring_breakdown = {
            item["id"]: {
                "name": item["name"],
                "score": item["score"],
                "max_score": item["max_score"],
                "score_ratio": item["score_ratio"],
                "weight": item["weight"],
                "confidence": item["confidence"],
                "reason": item["reason"],
                "evidence_quotes": item["evidence_quotes"],
                "missing_requirements": item["missing_requirements"],
            }
            for item in dimension_results
        }

        details = {
            "type": "report",
            "scoring_mode": "rubric_dimension_evidence",
            "rubric_mode": rubric["mode"],
            "report_chunk_count": chunk_count,
            "dimension_results": dimension_results,
            "scoring_breakdown": scoring_breakdown,
            "suggestions": suggestions,
            "needs_manual_review": needs_manual_review,
            "grade_level": ReportGraderAgent._get_grade_level(final_score, max_score),
            "visual_evidence": visual_evidence or None,
        }

        return {
            "score": final_score,
            "max_score": max_score,
            "confidence": confidence,
            "feedback": feedback,
            "details": details,
        }

    @staticmethod
    def _collect_unique_suggestions(dimension_results: List[dict]) -> List[str]:
        suggestions = []
        for item in dimension_results:
            for suggestion in item.get("suggestions", []):
                if suggestion and suggestion not in suggestions:
                    suggestions.append(suggestion)
                if len(suggestions) >= 4:
                    return suggestions
        return suggestions

    @staticmethod
    def _build_feedback(
        final_score: float,
        max_score: float,
        dimension_results: List[dict],
        needs_manual_review: bool,
    ) -> str:
        weakest = sorted(dimension_results, key=lambda item: item["score_ratio"])[:2]
        strongest = sorted(dimension_results, key=lambda item: item["score_ratio"], reverse=True)[:1]

        parts = [f"本报告按评分细则完成逐项评估，得分 {final_score}/{max_score}。"]
        if strongest:
            parts.append(f"相对较好的部分是“{strongest[0]['name']}”。")
        if weakest:
            weak_names = "、".join(item["name"] for item in weakest)
            parts.append(f"主要扣分集中在“{weak_names}”，建议补充更明确的证据、过程说明和结果解释。")
        if needs_manual_review:
            parts.append("由于部分维度证据不足或置信度偏低，建议教师进行人工复核。")
        return "".join(parts)

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
            summary_prompt = CONCISE_SUMMARY_PROMPT.replace("{query}", report)
            summary = await self.ai_handler.get_completion(summary_prompt)
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
                "type": "report",
                "scoring_mode": "rubric_dimension_evidence",
                "grade_level": "不及格",
                "reason": reason,
                "needs_manual_review": True,
                "dimension_results": [],
                "scoring_breakdown": {},
                "suggestions": [],
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
                "type": "report",
                "scoring_mode": "rubric_dimension_evidence",
                "grade_level": "待定",
                "error": error_msg,
                "needs_manual_review": True,
                "dimension_results": [],
                "scoring_breakdown": {},
                "suggestions": ["请教师人工复核本次评分"],
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
