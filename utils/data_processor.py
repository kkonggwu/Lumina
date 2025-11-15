#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: data_processor.py
@Author: kkonggwu
@Date: 2025/11/13
@Version: 2.0 - 增强元信息存储版本
"""
import hashlib
import logging
import uuid
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


class DataProcessor:
    CATEGORY_MAPPING = {
        # 核心基础类
        'os': '操作系统',
        'network': '计算机网络',
        'db': '数据库系统',
        'algo': '算法与数据结构',
        'compiler': '编译原理',
        'arch': '计算机组成原理',
        'cs_base': '计算机基础',
        'math': '数学基础',
        'security': '网络安全',
    }
    CATEGORY_LABELS = list(set(CATEGORY_MAPPING.values()))

    def __init__(self, data_path: str):
        """
        初始化数据准备模块

        Args:
            data_path: 数据文件夹路径
        """
        self.data_path = Path(data_path)
        self.documents: List[Document] = []  # 父文档
        self.chunks: List[Document] = []  # 子文档（按标题分割的小块）
        self.parent_child_map: Dict[str, str] = {}  # 子块ID -> 父文档ID的映射
        self.processed_time = datetime.now().isoformat()

    def load_documents(self) -> List[Document]:
        """
        加载文档数据 - 增强元信息版本

        Returns:
            加载的文档列表
        """
        logger.info(f"正在从 {self.data_path} 加载文档...")

        documents = []

        # 支持多种文档格式
        supported_extensions = ['*.md', '*.txt', '*.markdown']

        for extension in supported_extensions:
            for md_file in self.data_path.rglob(extension):
                try:
                    # 直接读取文件内容，保持原始格式
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 为每个父文档分配确定性的唯一ID（基于数据根目录的相对路径）
                    try:
                        relative_path = md_file.resolve().relative_to(self.data_path.resolve()).as_posix()
                    except Exception:
                        relative_path = md_file.as_posix()

                    parent_id = hashlib.md5(relative_path.encode("utf-8")).hexdigest()

                    # 创建Document对象
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": str(md_file),
                            "parent_id": parent_id,
                            "doc_type": "parent",  # 标记为父文档
                            "processor_version": "2.0",
                            "processed_time": self.processed_time
                        }
                    )

                    # 增强元数据
                    self._enhance_metadata(doc)
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"读取文件 {md_file} 失败: {e}")

        self.documents = documents
        logger.info(f"成功加载 {len(documents)} 个文档")
        return documents

    def _enhance_metadata(self, doc: Document):
        """
        增强文档元数据 - 完整版本

        Args:
            doc: 需要增强元数据的文档
        """
        file_path = Path(doc.metadata.get('source', ''))

        # 基础文件信息
        file_stats = file_path.stat() if file_path.exists() else None

        # 获取文件时间信息
        if file_stats:
            created_time = datetime.fromtimestamp(file_stats.st_ctime).isoformat()
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
        else:
            created_time = modified_time = "未知"

        # 内容分析
        content = doc.page_content
        lines = content.split('\n')
        words = content.split()

        # 检测文档特征
        features = self._detect_document_features(content)

        # 更新元数据
        doc.metadata.update({
            # 文件信息
            'course_name': file_path.stem,
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_extension': file_path.suffix.lower(),
            'file_size': file_stats.st_size if file_stats else 0,
            'file_created': created_time,
            'file_modified': modified_time,
            'relative_path': self._get_relative_path(file_path),

            # 内容统计
            'content_length': len(content),
            'line_count': len(lines),
            'word_count_approx': len(words),
            'char_count': len(content.replace('\n', '')),
            'non_empty_line_count': len([line for line in lines if line.strip()]),

            # 分类信息
            'category': self._detect_category(file_path),
            'subcategory': self._detect_subcategory(file_path),

            # 文档特征
            **features,

            # 处理信息
            'chunked': False,  # 将在分块后更新
            'enhanced_metadata': True,
        })

    def _detect_category(self, file_path: Path) -> str:
        """检测文档主分类"""
        path_parts = file_path.parts
        for key, value in self.CATEGORY_MAPPING.items():
            if key in path_parts:
                return value
        return '其他'

    def _detect_subcategory(self, file_path: Path) -> str:
        """检测文档子分类"""
        path_parts = file_path.parts
        parent_dir = file_path.parent.name.lower()

        # 基于父目录名称推断子分类
        subcategory_keywords = {
            'basic': '基础',
            'advanced': '进阶',
            'tutorial': '教程',
            'practice': '实践',
            'theory': '理论',
            'lab': '实验',
            'exam': '考试',
            'homework': '作业'
        }

        for keyword, chinese in subcategory_keywords.items():
            if keyword in parent_dir:
                return chinese

        return '通用'

    def _detect_document_features(self, content: str) -> Dict[str, Any]:
        """检测文档内容特征"""
        return {
            'has_code_blocks': '```' in content,
            'has_math_formulas': any(char in content for char in ['$', '$$', '\\[']),
            'has_tables': '|' in content and any(sep in content for sep in ['---', '===']),
            'has_images': '![' in content,
            'has_links': any(prefix in content for prefix in ['http://', 'https://', 'www.']),
            'has_headings': any(line.strip().startswith('#') for line in content.split('\n')[:10]),
            'has_lists': any(line.strip().startswith(('-', '*', '+', '1.', '2.'))
                             for line in content.split('\n')[:20]),
            'has_diagrams': any(keyword in content.lower()
                                for keyword in ['graph', 'diagram', 'flowchart', 'sequence']),
        }

    def _get_relative_path(self, file_path: Path) -> str:
        """获取相对于数据根目录的路径"""
        try:
            return file_path.resolve().relative_to(self.data_path.resolve()).as_posix()
        except Exception:
            return file_path.as_posix()

    @classmethod
    def get_supported_categories(cls) -> List[str]:
        """对外提供支持的分类标签列表"""
        return cls.CATEGORY_LABELS

    def chunk_documents(self) -> List[Document]:
        """
        Markdown结构感知分块 - 增强元信息版本

        Returns:
            分块后的文档列表
        """
        logger.info("正在进行Markdown结构感知分块...")

        if not self.documents:
            raise ValueError("请先加载文档")

        # 使用Markdown标题分割器
        chunks = self._markdown_header_split()

        # 为每个chunk添加增强元数据
        for i, chunk in enumerate(chunks):
            self._enhance_chunk_metadata(chunk, i)

        self.chunks = chunks
        logger.info(f"Markdown分块完成，共生成 {len(chunks)} 个chunk")

        # 更新父文档的分块状态
        for doc in self.documents:
            doc.metadata['chunked'] = True
            doc.metadata['chunk_count'] = len([c for c in chunks
                                               if c.metadata.get('parent_id') == doc.metadata.get('parent_id')])

        return chunks

    def _markdown_header_split(self) -> List[Document]:
        """
        使用Markdown标题分割器进行结构化分割 - 增强版本

        Returns:
            按标题结构分割的文档列表
        """
        # 定义要分割的标题层级
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4")
        ]

        # 创建Markdown分割器
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,  # 保留标题，便于理解上下文
            return_each_line=False
        )

        all_chunks = []

        for doc in self.documents:
            try:
                # 检查文档是否适合Markdown分割
                if not self._is_markdown_document(doc):
                    logger.warning(f"文档 {doc.metadata.get('course_name', '未知')} 不适合Markdown分割，将作为整体处理")
                    all_chunks.append(doc)
                    continue

                # 对每个文档进行Markdown分割
                md_chunks = markdown_splitter.split_text(doc.page_content)

                logger.debug(f"文档 {doc.metadata.get('course_name', '未知')} 分割成 {len(md_chunks)} 个chunk")

                # 为每个子块建立与父文档的关系
                parent_id = doc.metadata["parent_id"]

                for i, chunk in enumerate(md_chunks):
                    # 为子块分配唯一ID
                    child_id = str(uuid.uuid4())

                    # 合并原文档元数据和新的标题元数据
                    chunk.metadata.update(doc.metadata)
                    chunk.metadata.update({
                        "chunk_id": child_id,
                        "parent_id": parent_id,
                        "doc_type": "child",  # 标记为子文档
                        "chunk_index": i,  # 在父文档中的位置
                        "is_structured_chunk": True,  # 标记为结构化分块
                    })

                    # 建立父子映射关系
                    self.parent_child_map[child_id] = parent_id

                    all_chunks.append(chunk)

            except Exception as e:
                logger.warning(f"文档 {doc.metadata.get('source', '未知')} Markdown分割失败: {e}")
                # 如果Markdown分割失败，将整个文档作为一个chunk
                doc.metadata.update({
                    "chunk_id": str(uuid.uuid4()),
                    "is_structured_chunk": False,
                    "chunk_failed_reason": str(e)
                })
                all_chunks.append(doc)

        logger.info(f"Markdown结构分割完成，生成 {len(all_chunks)} 个结构化块")
        return all_chunks

    def _is_markdown_document(self, doc: Document) -> bool:
        """检查文档是否适合Markdown分割"""
        content = doc.page_content
        lines = content.split('\n')[:20]  # 检查前20行

        # 检查是否有Markdown标题
        has_headers = any(line.strip().startswith('#') for line in lines if line.strip())

        # 检查内容长度是否适合分割
        is_long_enough = len(content) > 200

        return has_headers and is_long_enough

    def _enhance_chunk_metadata(self, chunk: Document, batch_index: int):
        """增强chunk元数据"""
        content = chunk.page_content
        lines = content.split('\n')

        # 提取标题信息
        header_hierarchy = []
        header_levels = ['h1', 'h2', 'h3', 'h4']

        for level in header_levels:
            if level in chunk.metadata:
                header_text = chunk.metadata[level].strip()
                if header_text:
                    header_hierarchy.append(header_text)

        # 计算内容特征
        chunk_metadata_updates = {
            "batch_index": batch_index,
            "chunk_size": len(content),
            "chunk_line_count": len(lines),
            "chunk_word_count": len(content.split()),
            "header_hierarchy": " > ".join(header_hierarchy),
            "header_level": len(header_hierarchy),
            "is_section_header": len(header_hierarchy) > 0,
            "starts_with_header": any(line.strip().startswith('#') for line in lines[:2]),
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
        }

        chunk.metadata.update(chunk_metadata_updates)

    def filter_documents_by_category(self, category: str) -> List[Document]:
        """
        按分类过滤文档

        Args:
            category: 课程分类

        Returns:
            过滤后的文档列表
        """
        return [doc for doc in self.documents if doc.metadata.get('category') == category]

    def filter_chunks_by_feature(self, feature: str, value: Any = True) -> List[Document]:
        """
        按文档特征过滤chunks

        Args:
            feature: 特征名称
            value: 特征值

        Returns:
            过滤后的chunk列表
        """
        return [chunk for chunk in self.chunks if chunk.metadata.get(feature) == value]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取增强的数据统计信息

        Returns:
            统计信息字典
        """
        if not self.documents:
            return {}

        stats = {
            'total_documents': len(self.documents),
            'total_chunks': len(self.chunks),
            'categories': {},
            'file_types': {},
            'document_features': {},
            'chunk_statistics': {},
            'processing_info': {
                'processor_version': '2.0',
                'processed_time': self.processed_time,
                'data_source': str(self.data_path)
            }
        }

        # 分类统计
        for doc in self.documents:
            category = doc.metadata.get('category', '未知')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1

            file_type = doc.metadata.get('file_extension', '未知')
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1

        # 文档特征统计
        feature_counts = {}
        for doc in self.documents:
            for feature in ['has_code_blocks', 'has_math_formulas', 'has_tables', 'has_images', 'has_links']:
                if doc.metadata.get(feature):
                    feature_counts[feature] = feature_counts.get(feature, 0) + 1
        stats['document_features'] = feature_counts

        # Chunk统计
        if self.chunks:
            chunk_sizes = [chunk.metadata.get('chunk_size', 0) for chunk in self.chunks]
            header_levels = [chunk.metadata.get('header_level', 0) for chunk in self.chunks]

            stats['chunk_statistics'] = {
                'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
                'max_chunk_size': max(chunk_sizes),
                'min_chunk_size': min(chunk_sizes),
                'avg_header_level': sum(header_levels) / len(header_levels),
                'chunks_with_headers': len([c for c in self.chunks if c.metadata.get('is_section_header')]),
                'structured_chunks': len([c for c in self.chunks if c.metadata.get('is_structured_chunk')]),
            }

        return stats

    def export_metadata(self, output_path: str, export_type: str = "all"):
        """
        导出元数据到JSON文件 - 增强版本

        Args:
            output_path: 输出文件路径
            export_type: 导出类型 ("documents", "chunks", "all")
        """
        import json

        output_data = {
            'export_time': datetime.now().isoformat(),
            'processor_version': '2.0',
            'statistics': self.get_statistics()
        }

        if export_type in ["documents", "all"]:
            documents_metadata = []
            for doc in self.documents:
                doc_meta = {k: v for k, v in doc.metadata.items()
                            if k not in ['page_content']}  # 排除大文本内容
                doc_meta['content_preview'] = doc.page_content[:200] + "..." if len(
                    doc.page_content) > 200 else doc.page_content
                documents_metadata.append(doc_meta)
            output_data['documents'] = documents_metadata

        if export_type in ["chunks", "all"] and self.chunks:
            chunks_metadata = []
            for chunk in self.chunks:
                chunk_meta = {k: v for k, v in chunk.metadata.items()
                              if k not in ['page_content']}
                chunk_meta['content_preview'] = chunk.page_content[:100] + "..." if len(
                    chunk.page_content) > 100 else chunk.page_content
                chunks_metadata.append(chunk_meta)
            output_data['chunks'] = chunks_metadata

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"元数据已导出到: {output_path} (类型: {export_type})")

    def get_parent_documents(self, child_chunks: List[Document]) -> List[Document]:
        """
        根据子块获取对应的父文档（智能去重）- 增强版本

        Args:
            child_chunks: 检索到的子块列表

        Returns:
            对应的父文档列表（去重，按相关性排序）
        """
        # 统计每个父文档被匹配的次数和相关性信息
        parent_relevance = {}
        parent_docs_map = {}
        parent_chunk_details = {}

        # 收集所有相关的父文档ID和相关性信息
        for chunk in child_chunks:
            parent_id = chunk.metadata.get("parent_id")
            if parent_id:
                # 增加相关性计数
                parent_relevance[parent_id] = parent_relevance.get(parent_id, 0) + 1

                # 收集匹配的chunk信息
                if parent_id not in parent_chunk_details:
                    parent_chunk_details[parent_id] = []

                parent_chunk_details[parent_id].append({
                    'chunk_id': chunk.metadata.get('chunk_id'),
                    'header': chunk.metadata.get('header_hierarchy', '无标题'),
                    'content_preview': chunk.metadata.get('content_preview', ''),
                    'chunk_size': chunk.metadata.get('chunk_size', 0)
                })

                # 缓存父文档（避免重复查找）
                if parent_id not in parent_docs_map:
                    for doc in self.documents:
                        if doc.metadata.get("parent_id") == parent_id:
                            parent_docs_map[parent_id] = doc
                            break

        # 按相关性排序（匹配次数多的排在前面）
        sorted_parent_ids = sorted(parent_relevance.keys(),
                                   key=lambda x: parent_relevance[x],
                                   reverse=True)

        # 构建去重后的父文档列表，并添加相关性信息
        parent_docs = []
        for parent_id in sorted_parent_ids:
            if parent_id in parent_docs_map:
                doc = parent_docs_map[parent_id]
                # 添加相关性信息到文档元数据
                doc.metadata['relevance_score'] = parent_relevance[parent_id]
                doc.metadata['matched_chunks'] = parent_chunk_details[parent_id]
                doc.metadata['match_ratio'] = parent_relevance[parent_id] / doc.metadata.get('chunk_count', 1)
                parent_docs.append(doc)

        # 收集父文档名称和相关性信息用于日志
        parent_info = []
        for doc in parent_docs:
            course_name = doc.metadata.get('course_name', '未知课程')
            relevance_count = doc.metadata.get('relevance_score', 0)
            match_ratio = doc.metadata.get('match_ratio', 0)
            parent_info.append(f"{course_name}({relevance_count}块, {match_ratio:.1%})")

        logger.info(f"从 {len(child_chunks)} 个子块中找到 {len(parent_docs)} 个去重父文档: {', '.join(parent_info)}")
        return parent_docs

    def find_similar_documents(self, category: str = None, min_size: int = None,
                               has_features: List[str] = None) -> List[Document]:
        """
        查找相似特征的文档

        Args:
            category: 分类过滤
            min_size: 最小文件大小
            has_features: 必须包含的特征列表

        Returns:
            符合条件的文档列表
        """
        filtered_docs = self.documents

        if category:
            filtered_docs = [doc for doc in filtered_docs if doc.metadata.get('category') == category]

        if min_size:
            filtered_docs = [doc for doc in filtered_docs if doc.metadata.get('file_size', 0) >= min_size]

        if has_features:
            for feature in has_features:
                filtered_docs = [doc for doc in filtered_docs if doc.metadata.get(feature, False)]

        return filtered_docs