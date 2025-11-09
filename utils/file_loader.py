from __future__ import annotations

from typing import Dict, List, Tuple

from io import BytesIO


def load_txt(content: bytes) -> str:
    """
    加载文本文件内容

    Args:
        content: 文件字节内容

    Returns:
        解码后的文本内容
    """
    return content.decode("utf-8", errors="ignore")


def load_pdf(content: bytes) -> str:
    """
    加载PDF文件内容

    Args:
        content: PDF文件字节内容

    Returns:
        提取的文本内容
    """
    try:
        from pypdf import PdfReader
    except Exception:
        # 退化处理：若无依赖，返回空字符串
        return ""
    reader = PdfReader(BytesIO(content))
    texts: List[str] = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)


def load_docx(content: bytes) -> str:
    """
    加载Word文档内容

    Args:
        content: Word文档字节内容

    Returns:
        提取的文本内容
    """
    try:
        import docx  # python-docx
    except Exception:
        return ""
    doc = docx.Document(BytesIO(content))
    return "\n".join([p.text for p in doc.paragraphs])


def sniff_and_load(filename: str, content: bytes) -> Tuple[str, dict]:
    """
    根据文件扩展名自动选择加载器

    Args:
        filename: 文件名
        content: 文件字节内容

    Returns:
        元组：(提取的文本内容, 文件元数据)
    """
    name_lower = filename.lower()
    if name_lower.endswith(".txt"):
        return load_txt(content), {"filename": filename, "type": "txt"}
    if name_lower.endswith(".pdf"):
        return load_pdf(content), {"filename": filename, "type": "pdf"}
    if name_lower.endswith(".docx"):
        return load_docx(content), {"filename": filename, "type": "docx"}
    # 默认按文本尝试
    return load_txt(content), {"filename": filename, "type": "txt"}



