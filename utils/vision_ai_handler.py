#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态模型调用封装，用于报告图表宽松识别。
"""
import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Dict, List

from openai import AsyncOpenAI

from config.config import APIConfig, DASHSCOPE_API_KEY
from utils.logger import get_logger
from utils.prompt_template import VISION_CHART_PROMPT

logger = get_logger("vision_ai_handler")





class VisionAIHandler:
    """调用 Qwen-VL 兼容接口进行图表识别。"""

    def __init__(self, provider: str = "qwen"):
        config = APIConfig.get_config(provider)
        self.client = AsyncOpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=config["api_base"],
        )
        self.model = os.getenv("QWEN_VL_MODEL", "qwen-vl-plus")

    async def aclose(self):
        close = getattr(self.client, "aclose", None) or getattr(self.client, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def analyze_report_images(self, images: List[Dict], max_images: int = 12) -> Dict:
        findings = []
        for image in images[:max_images]:
            findings.append(await self.analyze_chart_image(image))

        charts_detected = sorted({
            chart_type
            for finding in findings
            for chart_type in finding.get("chart_types", [])
        })
        return {
            "charts_detected": charts_detected,
            "chart_findings": findings,
            "visual_summary": self._build_visual_summary(findings),
        }

    async def analyze_chart_image(self, image: Dict) -> Dict:
        image_path = image.get("image_path", "")
        try:
            data_url = self._image_to_data_url(image_path)
            prompt = VISION_CHART_PROMPT.format(
                nearby_text=(image.get("nearby_text") or "")[:1000]
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=800,
                temperature=0.1,
            )
            raw = response.choices[0].message.content or ""
            parsed = self._parse_json_response(raw)
        except Exception as e:
            logger.warning(f"多模态图表识别失败: {str(e)}")
            parsed = {
                "has_chart": False,
                "chart_types": [],
                "is_probability_plot": False,
                "axes_readable": False,
                "analysis_quality_hint": f"图表识别失败: {str(e)}",
                "confidence": 0.0,
                "requires_manual_review": True,
            }

        return {
            "image_path": image_path,
            "page": image.get("page"),
            "image_index": image.get("image_index"),
            "kind": image.get("kind"),
            **self._normalize_result(parsed),
        }

    @staticmethod
    def _image_to_data_url(image_path: str) -> str:
        path = Path(image_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        text = (text or "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"无法解析多模态模型 JSON: {text[:200]}")

    @staticmethod
    def _normalize_result(result: dict) -> dict:
        chart_types = result.get("chart_types", [])
        if isinstance(chart_types, str):
            chart_types = [chart_types]
        return {
            "has_chart": bool(result.get("has_chart")),
            "chart_types": [str(item) for item in chart_types],
            "is_probability_plot": bool(result.get("is_probability_plot")),
            "axes_readable": bool(result.get("axes_readable")),
            "analysis_quality_hint": str(result.get("analysis_quality_hint", "")),
            "confidence": max(0.0, min(float(result.get("confidence", 0.0) or 0.0), 1.0)),
            "requires_manual_review": bool(result.get("requires_manual_review", False)),
        }

    @staticmethod
    def _build_visual_summary(findings: List[Dict]) -> str:
        if not findings:
            return "未抽取到可供识别的报告图片或页面截图。"
        chart_count = sum(1 for item in findings if item.get("has_chart"))
        chart_types = sorted({
            chart_type
            for item in findings
            for chart_type in item.get("chart_types", [])
        })
        return f"共分析 {len(findings)} 张图片/页面，检测到 {chart_count} 张包含图表；图表类型：{', '.join(chart_types) or '未明确识别'}。"
