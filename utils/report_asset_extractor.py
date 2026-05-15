#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告附件资源抽取：正文、文本块、页面截图和内嵌图片。
"""
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.file_loader import sniff_and_load
from utils.logger import get_logger

logger = get_logger("report_asset_extractor")


class ReportAssetExtractor:
    """从 PDF/DOCX 报告中抽取文本与视觉材料。"""

    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    SEPARATORS = ["\n\n", "\n", "。", "；", "！", "？", ".", " ", ""]
    MAX_PDF_PAGES = 12
    MAX_DOCX_IMAGES = 20

    @classmethod
    def extract(cls, file_path: Path, output_root: Path) -> Dict:
        output_root.mkdir(parents=True, exist_ok=True)
        content = file_path.read_bytes()
        text, metadata = sniff_and_load(file_path.name, content)
        file_type = metadata.get("type", file_path.suffix.lower().lstrip("."))

        result = {
            "text": text or "",
            "chunks": cls._split_text(text or ""),
            "images": [],
            "warnings": [],
        }

        if file_type == "pdf":
            result["images"] = cls._extract_pdf_pages(file_path, output_root, metadata.get("page_map", []))
        elif file_type == "docx":
            result["images"] = cls._extract_docx_images(file_path, output_root)

        return result

    @classmethod
    def _split_text(cls, text: str) -> List[str]:
        if not text.strip():
            return []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cls.CHUNK_SIZE,
            chunk_overlap=cls.CHUNK_OVERLAP,
            separators=cls.SEPARATORS,
        )
        return [doc.page_content for doc in splitter.create_documents([text]) if doc.page_content.strip()]

    @classmethod
    def _extract_pdf_pages(cls, file_path: Path, output_root: Path, page_map: List[dict]) -> List[dict]:
        """
        将 PDF 前若干页渲染为图片。PyMuPDF 不可用时返回空列表，不影响文本评分。
        """
        try:
            import fitz  # PyMuPDF
        except Exception as e:
            logger.warning(f"PyMuPDF 不可用，跳过 PDF 页面截图: {str(e)}")
            return []

        images = []
        doc = fitz.open(file_path)
        page_count = min(len(doc), cls.MAX_PDF_PAGES)
        for page_index in range(page_count):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image_path = output_root / f"page_{page_index + 1}.jpg"
            pix.save(str(image_path))

            nearby_text = ""
            if page_index < len(page_map):
                try:
                    nearby_text = page.get_text("text")[:1000]
                except Exception:
                    nearby_text = ""

            images.append({
                "kind": "pdf_page",
                "page": page_index + 1,
                "image_path": str(image_path),
                "nearby_text": nearby_text,
            })
        doc.close()
        return images

    @classmethod
    def _extract_docx_images(cls, file_path: Path, output_root: Path) -> List[dict]:
        """从 docx zip 包中抽取内嵌图片。"""
        images = []
        with zipfile.ZipFile(file_path, "r") as archive:
            media_files = [
                name for name in archive.namelist()
                if name.startswith("word/media/") and not name.endswith("/")
            ][:cls.MAX_DOCX_IMAGES]

            for index, member in enumerate(media_files, 1):
                extension = Path(member).suffix.lower() or ".bin"
                image_path = output_root / f"docx_image_{index}{extension}"
                with archive.open(member) as source, open(image_path, "wb") as target:
                    shutil.copyfileobj(source, target)
                images.append({
                    "kind": "docx_image",
                    "image_index": index,
                    "image_path": str(image_path),
                    "nearby_text": "",
                })
        return images
