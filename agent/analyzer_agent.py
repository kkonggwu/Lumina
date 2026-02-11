#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: analyzer_agent.py
@Author: kkonggwu
@Date: 2026/1/31
@Version: 1.0
"""
import json
import logging
import re
from typing import Optional, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from utils.ai_handler import AIHandler
from utils.prompt_template import AGENT_KEYPOINT_EXTRACTION_PROMPT, AGENT_KEYPOINT_COMPARISON_PROMPT

logger = logging.getLogger('analyzer_agent')
class AnalyzerAgent:
    """
    分析者，负责对数据进行分析处理，包括对问题、标准答案、学生答案和参考资料的分析，然后生成关键点
    """
    def __init__(self, provider: str = "qwen"):
        self.ai_handler = AIHandler.create_default(provider=provider)
        self.extraction_chain = self._build_extraction_chain()
        self.comparison_chain = self._build_comparison_chain()

    def _build_extraction_chain(self):
        """
        构建关键掉提取链
        :return:
        """
        prompt = PromptTemplate.from_template(AGENT_KEYPOINT_EXTRACTION_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    def _build_comparison_chain(self):
        """
        构建关键点对比链
        :return:
        """
        prompt = PromptTemplate.from_template(AGENT_KEYPOINT_COMPARISON_PROMPT)
        return prompt | self.ai_handler.llm | StrOutputParser()

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """
        从 LLM 返回的文本中解析 JSON，支持多种格式

        尝试顺序：
        1. 直接解析整个文本
        2. 提取 markdown 代码块中的 JSON
        3. 提取第一个 {} 对象

        :param text: LLM 返回的文本
        :return: 解析后的字典
        :raises ValueError: 所有解析尝试都失败时
        """
        if not text or not text.strip():
            raise ValueError("输入文本为空")

        text = text.strip()

        # 尝试1: 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试2: 提取 markdown 代码块 (```json ... ``` 或 ``` ... ```)
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试3: 提取第一个完整的 JSON 对象 {...}
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # 所有尝试都失败
        logger.error(f"JSON 解析失败，原始文本：{text[:500]}")
        raise ValueError(f"无法从 LLM 返回中解析 JSON：{text[:200]}...")

    async def analyze_standard_answer(self, question, standard_answer) -> dict:
        """
        场景A: 教师提取标准答案的关键要点
        :param question:
        :param standard_answer:
        :return:
        """
        logger.info(f"[场景A]: 开始分析标准答案的关键要点，题目：{question[:50]}")
        try:
            # 调用关键点提取链
            raw_result = await self.extraction_chain.ainvoke({
                "answer_type": "标准答案",
                "question": question,
                "answer": standard_answer
            })
            result = self._parse_json_response(raw_result)
            keypoints = result.get("keypoints", [])
            logger.info(f"[场景A]：标准答案分析完成，提取到 {len(keypoints)} 个关键点")
            return {
                "keypoints": keypoints,
                "keypoint_count": result.get("keypoint_count", len(keypoints)),
                "summary": result.get("summary", ""),
                "quality_score": result.get("quality_score", 0.0),
                "difficulty_estimate": result.get("difficulty_estimate", "medium"),
                "success": True
            }
        except Exception as e:
            logger.error(f"[场景A]：标准答案分析失败：{str(e)}")
            return {
                "keypoints": [],
                "keypoint_count": 0,
                "summary": "",
                "quality_score": 0.0,
                "difficulty_estimate": "medium",
                "success": False,
                "error": str(e)
            }

    async def analyze_student_answer(self, question: str,
                                     student_answer:str,
                                     standard_keypoints: List[str],
                                     reference_materials: Optional[List[dict]] = None):
        """
        场景B:提取学生答案的关键要点，并与标准关键要点进行对比
        :param question:
        :param student_answer:
        :param standard_keypoints:
        :param reference_materials:
        :return:
        """
        logger.info(f"场景B：开始分析学生答案，题目：{question[:50]}")
        try:
            # 1. 提取学生答案关键要点
            raw_result = await self.extraction_chain.ainvoke({
                "answer_type": "学生答案",
                "question": question,
                "answer": student_answer
            })
            extraction_result = self._parse_json_response(raw_result)
            student_keypoints = extraction_result.get("keypoints", [])

            logger.info(f"场景B：学生关键点提取完成，共 {len(student_keypoints)} 条")

            # 2. 与标准关键要点对比
            raw_comparison = await self.comparison_chain.ainvoke({
                "question": question,
                "standard_keypoints": self._format_keypoints_for_prompt(standard_keypoints),
                "student_keypoints": self._format_keypoints_for_prompt(student_keypoints),
                "reference_materials": self._format_materials_for_prompt(reference_materials)
            })
            comparison_result = self._parse_json_response(raw_comparison)

            # 提取对比结果
            missing = comparison_result.get("missing_keypoints", [])
            matching = comparison_result.get("matching_keypoints", [])
            redundant = comparison_result.get("redundant_keypoints", [])

            logger.info(
                f"场景B：对比完成：匹配 {len(matching)} 个，"
                f"缺失 {len(missing)} 个，冗余 {len(redundant)} 个"
            )

            return {
                "student_keypoints": student_keypoints,
                "matching_keypoints": matching,
                "missing_keypoints": missing,
                "redundant_keypoints": redundant,
                "coverage_rate": comparison_result.get("coverage_rate", 0.0),
                "overall_assessment": comparison_result.get("overall_assessment", ""),
                "success": True
            }
        except Exception as e:
            logger.error(f"[场景B] 学生答案分析失败：{str(e)}")
            return {
                "student_keypoints": [],
                "matching_keypoints": [],
                "missing_keypoints": [],
                "redundant_keypoints": [],
                "coverage_rate": 0.0,
                "overall_assessment": "",
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def _format_keypoints_for_prompt(keypoints: List[str]) -> str:
        """
        将关键要点列表格式化为 Prompt 中易读的文本
        :param keypoints: 关键要点列表
        :return: 格式化后的文本
        """
        if not keypoints:
            return "（无）"
        return "\n".join(f"  {i}. {kp}" for i, kp in enumerate(keypoints, 1))

    @staticmethod
    def _format_materials_for_prompt(materials: Optional[List[dict]]) -> str:
        """
        将参考资料格式化为 Prompt 中易读的文本
        :param materials: 参考资料列表
        :return: 格式化后的文本
        """
        if not materials:
            return "（无补充参考资料）"
        formatted = []
        for i, material in enumerate(materials[:3], 1):  # 最多取3条，避免 Prompt 过长
            content = material.get("content", "")
            # 截断过长的内容
            if len(content) > 500:
                content = content[:500] + "..."
            formatted.append(f"  参考资料{i}：{content}")
        return "\n".join(formatted)



    #
    #
    # async def analyze(self, question, standard_answer, student_answer, reference_materials):
    #     pass