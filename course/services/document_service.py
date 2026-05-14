#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档服务层
处理文档上传、删除、查询等业务逻辑
"""
import os
import uuid
from pathlib import Path
from typing import Tuple, Optional, List
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError
from django.conf import settings

from course.models import Document, Course, Enrollment
from user.models import UserModel
from user.user_service import UserService
from utils.langchain_milvus_manager import LangChainMilvusManager
from utils.file_loader import sniff_and_load
from utils.logger import get_logger

logger = get_logger('document_service')


class DocumentService:
    """文档服务类"""
    
    # 文档存储根目录
    DOCUMENT_STORAGE_ROOT = Path(settings.BASE_DIR) / 'staticfiles' / 'documents'
    
    # 支持的文档格式
    ALLOWED_EXTENSIONS = ['.md', '.txt', '.markdown', '.pdf', '.docx']
    
    def __init__(self):
        """初始化文档服务"""
        # 确保存储目录存在
        self.DOCUMENT_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        
        # 延迟初始化Milvus管理器（只在需要时初始化，避免影响查询性能）
        self._milvus_manager = None
    
    @property
    def milvus_manager(self):
        """延迟初始化Milvus管理器"""
        if self._milvus_manager is None:
            self._milvus_manager = LangChainMilvusManager(
                collection_name="documents",
                embedding_model="all-MiniLM-L6-v2"
            )
        return self._milvus_manager
    
    @staticmethod
    def check_upload_permission(user_id: int) -> Tuple[bool, str]:
        """
        检查用户是否有上传文档的权限
        
        Args:
            user_id: 用户ID
        
        Returns:
            tuple: (是否有权限, 错误消息)
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"
        
        # 只有管理员和教师可以上传
        if user.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
            return False, "只有管理员和教师可以上传文档"
        
        return True, ""
    
    @staticmethod
    def check_delete_permission(user_id: int) -> Tuple[bool, str]:
        """
        检查用户是否有删除文档的权限
        
        Args:
            user_id: 用户ID
        
        Returns:
            tuple: (是否有权限, 错误消息)
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"
        
        # 只有管理员和教师可以删除
        if user.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
            return False, "只有管理员和教师可以删除文档"
        
        return True, ""
    
    def upload_document(
        self,
        user_id: int,
        course_id: int,
        uploaded_file: UploadedFile
    ) -> Tuple[bool, str, Optional[Document]]:
        """
        上传文档并处理
        
        Args:
            user_id: 上传者ID
            course_id: 课程ID
            uploaded_file: 上传的文件对象
        
        Returns:
            tuple: (是否成功, 消息, Document对象)
        """
        try:
            # 1. 检查权限
            has_permission, error_msg = self.check_upload_permission(user_id)
            if not has_permission:
                return False, error_msg, None
            
            # 2. 验证课程是否存在
            try:
                course = Course.objects.get(id=course_id, is_deleted=False)
            except Course.DoesNotExist:
                return False, "课程不存在", None
            
            # 3. 验证用户是否存在
            user = UserService.get_user_by_id(user_id)
            if not user:
                return False, "用户不存在", None
            
            # 4. 生成唯一文件名和存储路径
            file_extension = Path(uploaded_file.name).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # 按课程ID组织文件存储
            course_storage_dir = self.DOCUMENT_STORAGE_ROOT / str(course_id)
            course_storage_dir.mkdir(parents=True, exist_ok=True)
            
            stored_path = course_storage_dir / unique_filename
            
            # 5. 保存文件到磁盘
            with open(stored_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            
            file_size = stored_path.stat().st_size
            
            # 6. 创建数据库记录（状态：上传中）
            document = Document(
                course=course,
                uploader=user,
                file_name=uploaded_file.name,
                stored_path=str(stored_path.relative_to(settings.BASE_DIR)),
                file_size=file_size,
                file_type=file_extension[1:] if file_extension else None,
                mime_type=uploaded_file.content_type,
                document_status=0,  # 上传中
                is_deleted=False
            )
            document.save()
            
            # 7. 处理文档内容并存入Milvus（异步处理，避免阻塞）
            try:
                self._process_and_index_document(document, stored_path)
            except Exception as e:
                logger.error(f"处理文档 {document.id} 失败: {str(e)}", exc_info=True)
                # 更新状态为处理失败
                document.document_status = 2  # 处理失败
                document.processing_log = f"处理失败: {str(e)}"
                document.save()
                return False, f"文档上传成功，但处理失败: {str(e)}", document
            
            return True, "文档上传并处理成功", document
            
        except Exception as e:
            logger.error(f"上传文档失败: {str(e)}", exc_info=True)
            return False, f"上传文档失败: {str(e)}", None
    
    # ---------- 切割策略常量 ----------
    _MD_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")]
    _PLAIN_CHUNK_SIZE = 800
    _PLAIN_CHUNK_OVERLAP = 150
    _PLAIN_SEPARATORS = ["\n\n", "\n", "。", "；", "！", "？", ".", " ", ""]

    def _process_and_index_document(self, document: Document, file_path: Path):
        """
        处理文档内容并索引到 Milvus。

        切割策略按文件类型分流：
          - .md / .markdown  → MarkdownHeaderTextSplitter（按 # 标题语义切割）
          - .docx            → 提取时已将 Heading 样式转为 # 前缀 → 同 md 策略
          - .pdf             → RecursiveCharacterTextSplitter，chunk 元数据携带页码范围
          - .txt / 其他      → RecursiveCharacterTextSplitter
        """
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()

            text_content, file_metadata = sniff_and_load(document.file_name, file_content)

            if not text_content or not text_content.strip():
                raise ValueError("文档内容为空，无法处理")

            from langchain_core.documents import Document as LangChainDocument
            from langchain_text_splitters import (
                MarkdownHeaderTextSplitter,
                RecursiveCharacterTextSplitter,
            )

            base_meta = {
                "source": str(file_path),
                "document_id": document.id,
                "course_id": document.course_id,
                "uploader_id": document.uploader_id,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
                **{k: v for k, v in file_metadata.items() if k != "page_map"},
            }

            file_type = file_metadata.get("type", "txt")
            chunks = self._split_by_type(
                text_content, file_type, file_metadata, base_meta,
                LangChainDocument, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter,
            )

            self.milvus_manager.add_documents(chunks)

            document.document_status = 1
            document.processing_log = (
                f"成功处理（{file_type}），生成 {len(chunks)} 个文档块，切割方式: "
                f"{'标题语义' if file_type in ('md', 'docx') else '字符窗口'}，已索引到 Milvus"
            )
            document.save()
            logger.info(f"文档 {document.id} 处理成功，类型={file_type}，生成 {len(chunks)} 个块")

        except Exception as e:
            logger.error(f"处理文档 {document.id} 时出错: {str(e)}", exc_info=True)
            raise

    def _split_by_type(
        self,
        text_content: str,
        file_type: str,
        file_metadata: dict,
        base_meta: dict,
        LangChainDocument,
        MarkdownHeaderTextSplitter,
        RecursiveCharacterTextSplitter,
    ):
        """
        根据文件类型选择切割策略，返回 LangChainDocument 列表。

        - md / docx：MarkdownHeaderTextSplitter 标题语义切割
        - pdf：RecursiveCharacterTextSplitter + 页码元数据注入
        - txt / 其他：RecursiveCharacterTextSplitter
        """
        if file_type in ("md", "docx"):
            return self._split_markdown_style(
                text_content, base_meta, LangChainDocument, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
            )
        elif file_type == "pdf":
            return self._split_pdf_style(
                text_content, file_metadata, base_meta,
                LangChainDocument, RecursiveCharacterTextSplitter
            )
        else:
            return self._split_plain_text(
                text_content, base_meta, LangChainDocument, RecursiveCharacterTextSplitter
            )

    def _split_markdown_style(
        self, text_content, base_meta, LangChainDocument, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
    ):
        """Markdown / Word（已转 # 前缀）→ 标题语义切割。"""
        # 对非标准 Markdown（无标题结构）长文档直接降级为滑动窗口切割，
        # 避免整篇作为超大块进入 embedding / prompt 流程。
        if (
            len(text_content) > self._PLAIN_CHUNK_SIZE
            and not self._has_markdown_headers(text_content)
        ):
            logger.info(
                "检测到非标准 Markdown 长文档（无 # 标题），降级为 RecursiveCharacterTextSplitter 滑动窗口切割"
            )
            return self._split_plain_text(
                text_content, base_meta, LangChainDocument, RecursiveCharacterTextSplitter
            )

        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self._MD_HEADERS,
            strip_headers=False,
            return_each_line=False,
        )
        try:
            chunks = splitter.split_text(text_content)
            for chunk in chunks:
                chunk.metadata.update(base_meta)
                chunk.metadata["split_method"] = "markdown_header"
            # 若整篇没有任何 # 标题，split_text 会返回 1 个大块；
            # 此时降级到通用切割，避免整篇一块影响检索
            if len(chunks) == 1 and len(chunks[0].page_content) > self._PLAIN_CHUNK_SIZE * 2:
                logger.info("文档无 Markdown 标题结构，降级为字符窗口切割")
                return self._split_plain_text(
                    text_content, base_meta, LangChainDocument, RecursiveCharacterTextSplitter
                )
            return chunks
        except Exception as e:
            logger.warning(f"Markdown 标题切割失败，降级为字符窗口切割: {e}")
            return self._split_plain_text(
                text_content, base_meta, LangChainDocument, RecursiveCharacterTextSplitter
            )

    @staticmethod
    def _has_markdown_headers(text_content: str) -> bool:
        """检测文本中是否包含 Markdown 标题结构。"""
        if not text_content:
            return False
        lines = text_content.splitlines()
        return any(line.lstrip().startswith("#") for line in lines if line.strip())

    def _split_pdf_style(
        self, text_content, file_metadata, base_meta,
        LangChainDocument, RecursiveCharacterTextSplitter
    ):
        """
        PDF → RecursiveCharacterTextSplitter，并为每个 chunk 注入页码范围。

        page_map 由 file_loader.load_pdf() 生成，格式：
            [{page_num, char_start, char_end}, ...]
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._PLAIN_CHUNK_SIZE,
            chunk_overlap=self._PLAIN_CHUNK_OVERLAP,
            separators=self._PLAIN_SEPARATORS,
        )
        raw_chunks = splitter.create_documents([text_content], metadatas=[base_meta])

        page_map = file_metadata.get("page_map", [])

        # 遍历 raw_chunks，根据 chunk 文本在全文中的偏移量推算页码
        full_text = text_content
        cursor = 0
        for chunk in raw_chunks:
            # 在全文中定位该 chunk 的起始偏移（从上次游标处向后搜索）
            idx = full_text.find(chunk.page_content[:50], cursor)
            if idx == -1:
                idx = cursor
            chunk_start = idx
            chunk_end = idx + len(chunk.page_content)

            pages_covered = self._pages_for_range(page_map, chunk_start, chunk_end)
            chunk.metadata["split_method"] = "recursive_char"
            chunk.metadata["page_start"] = pages_covered[0] if pages_covered else None
            chunk.metadata["page_end"] = pages_covered[-1] if pages_covered else None

            cursor = max(cursor, idx)

        return raw_chunks

    def _split_plain_text(
        self, text_content, base_meta, LangChainDocument, RecursiveCharacterTextSplitter
    ):
        """TXT / 其他格式 → RecursiveCharacterTextSplitter 通用切割。"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._PLAIN_CHUNK_SIZE,
            chunk_overlap=self._PLAIN_CHUNK_OVERLAP,
            separators=self._PLAIN_SEPARATORS,
        )
        chunks = splitter.create_documents([text_content], metadatas=[base_meta])
        for chunk in chunks:
            chunk.metadata["split_method"] = "recursive_char"
        return chunks

    @staticmethod
    def _pages_for_range(page_map: list, char_start: int, char_end: int) -> list:
        """返回 [char_start, char_end) 范围内覆盖的页码列表。"""
        pages = []
        for entry in page_map:
            if entry["char_end"] > char_start and entry["char_start"] < char_end:
                pages.append(entry["page_num"])
        return pages
    
    def delete_document(self, user_id: int, document_id: int) -> Tuple[bool, str]:
        """
        删除文档（逻辑删除，仅维护MySQL）
        
        Args:
            user_id: 操作者ID
            document_id: 文档ID
        
        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            # 1. 检查权限
            has_permission, error_msg = self.check_delete_permission(user_id)
            if not has_permission:
                return False, error_msg
            
            # 2. 查找文档
            try:
                document = Document.objects.get(id=document_id, is_deleted=False)
            except Document.DoesNotExist:
                return False, "文档不存在"
            
            # 3. 逻辑删除（仅更新MySQL，Milvus删除功能暂不实现）
            document.is_deleted = True
            document.save()
            
            logger.info(f"文档 {document_id} 已被用户 {user_id} 逻辑删除")
            
            return True, "文档删除成功"
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}", exc_info=True)
            return False, f"删除文档失败: {str(e)}"
    
    @staticmethod
    def get_document(document_id: int, user_id: Optional[int] = None) -> Optional[Document]:
        """
        获取文档详情
        
        Args:
            document_id: 文档ID
            user_id: 用户ID（可选，用于权限检查）
        
        Returns:
            Document对象，如果不存在返回None
        """
        try:
            # 使用select_related预加载关联对象，避免N+1查询
            document = Document.objects.select_related('course', 'uploader').get(
                id=document_id, 
                is_deleted=False
            )
            return document
        except Document.DoesNotExist:
            return None
    
    @staticmethod
    def list_documents(
        course_id: Optional[int] = None,
        user_id: Optional[int] = None,
        user=None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Document], int]:
        """
        获取文档列表
        
        Args:
            course_id: 课程ID（可选）
            user_id: 用户ID（可选）
            user: 当前登录用户；用于限制可见课程范围
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            tuple: (文档列表, 总数量)
        """
        try:
            # 使用select_related预加载关联对象，避免N+1查询问题
            query = Document.objects.select_related('course', 'uploader').filter(is_deleted=False)

            if user is not None:
                if not isinstance(user, UserModel):
                    try:
                        user = UserModel.objects.get(
                            id=getattr(user, "id", None),
                            is_deleted=UserModel.NOT_DELETED,
                        )
                    except UserModel.DoesNotExist:
                        return [], 0

                if user.user_type == UserModel.TEACHER:
                    query = query.filter(course__teacher_id=user.id)
                elif user.user_type == UserModel.STUDENT:
                    enrolled_course_ids = Enrollment.objects.filter(
                        student=user,
                        enrollment_status=1,
                        is_deleted=False,
                    ).values_list('course_id', flat=True)
                    query = query.filter(course_id__in=enrolled_course_ids)
            
            # 按课程筛选
            if course_id:
                query = query.filter(course_id=course_id)
            
            # 按上传者筛选
            if user_id:
                query = query.filter(uploader_id=user_id)
            
            # 计算总数
            total = query.count()
            
            # 分页，使用索引优化排序
            documents = query.order_by('-uploaded_at')[offset:offset + limit]
            
            return list(documents), total
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}", exc_info=True)
            return [], 0
    
    @staticmethod
    def get_document_file_path(document: Document) -> Optional[Path]:
        """
        获取文档文件的完整路径
        
        Args:
            document: 文档对象
        
        Returns:
            文件路径，如果不存在返回None
        """
        try:
            file_path = Path(settings.BASE_DIR) / document.stored_path
            if file_path.exists():
                return file_path
            return None
        except Exception as e:
            logger.error(f"获取文档文件路径失败: {str(e)}")
            return None

