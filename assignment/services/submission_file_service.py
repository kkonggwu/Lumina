#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学生提交附件保存服务。
"""
import json
import uuid
from pathlib import Path
from typing import Dict, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from utils.logger import get_logger
from utils.report_asset_extractor import ReportAssetExtractor

logger = get_logger("submission_file_service")


class SubmissionFileService:
    """保存 report 题附件，并将附件解析结果写入 answers。"""

    STORAGE_ROOT = Path(settings.BASE_DIR) / "staticfiles" / "submission_reports"
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}
    MAX_FILE_SIZE = 30 * 1024 * 1024

    @classmethod
    def merge_report_files(
        cls,
        assignment_id: int,
        student_id: int,
        answers,
        files,
    ) -> Tuple[bool, str, Dict]:
        """
        将 multipart 中的 report_files_<question_id> 合并到 answers。
        """
        normalized_answers = cls._load_answers(answers)
        cls.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

        for field_name, uploaded_file in files.items():
            if not field_name.startswith("report_files_"):
                continue

            question_id = field_name.replace("report_files_", "", 1)
            if not question_id:
                return False, f"附件字段名非法: {field_name}", normalized_answers

            success, message, answer_payload = cls._save_and_extract(
                assignment_id=assignment_id,
                student_id=student_id,
                question_id=question_id,
                uploaded_file=uploaded_file,
            )
            if not success:
                return False, message, normalized_answers

            existing = normalized_answers.get(question_id)
            if isinstance(existing, dict):
                answer_payload["text_note"] = existing.get("text_note", existing.get("answer", ""))
            elif isinstance(existing, str):
                answer_payload["text_note"] = existing

            normalized_answers[question_id] = answer_payload

        return True, "", normalized_answers

    @classmethod
    def _save_and_extract(
        cls,
        assignment_id: int,
        student_id: int,
        question_id: str,
        uploaded_file: UploadedFile,
    ) -> Tuple[bool, str, Dict]:
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in cls.ALLOWED_EXTENSIONS:
            return False, "报告附件仅支持 PDF 或 DOCX", {}

        if uploaded_file.size and uploaded_file.size > cls.MAX_FILE_SIZE:
            return False, "报告附件不能超过 30MB", {}

        target_dir = cls.STORAGE_ROOT / str(assignment_id) / str(student_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4()}{extension}"
        stored_path = target_dir / unique_name

        with open(stored_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        try:
            extracted = ReportAssetExtractor.extract(stored_path, output_root=target_dir / "assets")
        except Exception as e:
            logger.warning(f"报告附件解析失败，将仅保存文件路径: {str(e)}", exc_info=True)
            extracted = {
                "text": "",
                "chunks": [],
                "images": [],
                "warnings": [f"附件解析失败: {str(e)}"],
            }

        relative_path = str(stored_path.relative_to(settings.BASE_DIR))
        return True, "", {
            "type": "file",
            "file_name": uploaded_file.name,
            "file_path": relative_path,
            "file_type": extension.lstrip("."),
            "text": extracted.get("text", ""),
            "chunks": extracted.get("chunks", []),
            "images": extracted.get("images", []),
            "warnings": extracted.get("warnings", []),
        }

    @staticmethod
    def _load_answers(answers) -> Dict:
        if isinstance(answers, dict):
            return dict(answers)
        if isinstance(answers, str):
            try:
                loaded = json.loads(answers)
                return loaded if isinstance(loaded, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
