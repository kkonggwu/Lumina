from __future__ import annotations

from typing import Dict, List, Tuple

from io import BytesIO


def load_txt(content: bytes) -> str:
    """加载纯文本文件内容"""
    return content.decode("utf-8", errors="ignore")


def load_pdf(content: bytes) -> Tuple[str, List[Dict]]:
    """
    加载 PDF 文件内容，保留页码元数据。

    Returns:
        (拼合后全文, 各页信息列表[{page_num, char_start, char_end}])
    """
    try:
        from pypdf import PdfReader
    except Exception:
        return "", []

    reader = PdfReader(BytesIO(content))
    texts: List[str] = []
    page_map: List[Dict] = []
    cursor = 0

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        # 每页之间用双换行分隔，方便后续按段落切割
        if texts:
            page_text = "\n\n" + page_text
        texts.append(page_text)
        page_map.append({
            "page_num": i + 1,
            "char_start": cursor,
            "char_end": cursor + len(page_text),
        })
        cursor += len(page_text)

    return "".join(texts), page_map


def load_docx(content: bytes) -> str:
    """
    加载 Word 文档内容，将 Heading 样式段落转换为 Markdown 标题格式。

    Word 中 "Heading 1" → "# 标题"，"Heading 2" → "## 标题"，以此类推（最深识别到 Heading 6）。
    普通段落直接保留文本，空白段落忽略。
    """
    try:
        import docx  # python-docx
    except Exception:
        return ""

    _HEADING_PREFIX = {
        "heading 1": "#",
        "heading 2": "##",
        "heading 3": "###",
        "heading 4": "####",
        "heading 5": "#####",
        "heading 6": "######",
    }

    doc = docx.Document(BytesIO(content))
    lines: List[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = para.style.name.lower() if para.style and para.style.name else ""
        prefix = _HEADING_PREFIX.get(style_name)
        if prefix:
            lines.append(f"{prefix} {text}")
        else:
            lines.append(text)

    return "\n\n".join(lines)


def sniff_and_load(filename: str, content: bytes) -> Tuple[str, dict]:
    """
    根据文件扩展名自动选择加载器。

    Returns:
        (提取的文本内容, 文件元数据)
        元数据中 pdf 额外含 "page_map" 字段（List[{page_num, char_start, char_end}]）
    """
    name_lower = filename.lower()

    if name_lower.endswith(".txt"):
        return load_txt(content), {"filename": filename, "type": "txt"}

    if name_lower.endswith((".md", ".markdown")):
        return load_txt(content), {"filename": filename, "type": "md"}

    if name_lower.endswith(".pdf"):
        text, page_map = load_pdf(content)
        return text, {"filename": filename, "type": "pdf", "page_map": page_map}

    if name_lower.endswith(".docx"):
        return load_docx(content), {"filename": filename, "type": "docx"}

    # 默认按 UTF-8 文本尝试
    return load_txt(content), {"filename": filename, "type": "txt"}



