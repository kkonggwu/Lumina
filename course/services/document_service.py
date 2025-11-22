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

from course.models import Document, Course
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
    
    def _process_and_index_document(self, document: Document, file_path: Path):
        """
        处理文档内容并索引到Milvus
        
        Args:
            document: 文档对象
            file_path: 文件路径
        """
        try:
            # 1. 读取文件内容
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 2. 使用file_loader提取文本内容
            text_content, file_metadata = sniff_and_load(document.file_name, file_content)
            
            if not text_content or not text_content.strip():
                raise ValueError("文档内容为空，无法处理")
            
            # 3. 使用LangChain进行文档分块
            from langchain_core.documents import Document as LangChainDocument
            from langchain_text_splitters import MarkdownHeaderTextSplitter
            
            # 创建临时文档对象
            langchain_doc = LangChainDocument(
                page_content=text_content,
                metadata={
                    "source": str(file_path),
                    "document_id": document.id,
                    "course_id": document.course_id,
                    "uploader_id": document.uploader_id,
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
                    **file_metadata
                }
            )
            
            # 使用Markdown分割器进行分块
            headers_to_split_on = [
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4")
            ]
            
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on,
                strip_headers=False,
                return_each_line=False
            )
            
            try:
                # 尝试Markdown分割
                chunks = markdown_splitter.split_text(text_content)
                # 为每个chunk添加元数据
                for chunk in chunks:
                    chunk.metadata.update(langchain_doc.metadata)
            except Exception as e:
                logger.warning(f"Markdown分割失败，将整个文档作为一个块: {str(e)}")
                # 如果分割失败，将整个文档作为一个块
                chunks = [langchain_doc]
            
            # 4. 使用LangChainMilvusManager的add_documents方法插入到Milvus
            # add_documents方法接受Document对象列表，会自动处理向量化
            milvus_ids = self.milvus_manager.add_documents(chunks)
            
            # 6. 更新文档状态为处理成功
            # DOCUMENT_STATUS_CHOICES: (0, '上传中'), (1, '处理成功'), (2, '处理失败')
            document.document_status = 1  # 处理成功
            document.processing_log = f"成功处理，生成 {len(chunks)} 个文档块，已索引到Milvus"
            document.save()
            
            logger.info(f"文档 {document.id} 处理成功，生成了 {len(chunks)} 个块")
            
        except Exception as e:
            logger.error(f"处理文档 {document.id} 时出错: {str(e)}", exc_info=True)
            raise
    
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
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Document], int]:
        """
        获取文档列表
        
        Args:
            course_id: 课程ID（可选）
            user_id: 用户ID（可选）
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            tuple: (文档列表, 总数量)
        """
        try:
            # 使用select_related预加载关联对象，避免N+1查询问题
            query = Document.objects.select_related('course', 'uploader').filter(is_deleted=False)
            
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

