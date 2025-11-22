#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档管理视图
"""
import os
from django.http import JsonResponse, FileResponse, Http404
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework.views import APIView
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from pathlib import Path

from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentListSerializer
)
from .services.document_service import DocumentService
from .models import Document


class DocumentUploadView(APIView):
    """文档上传视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="上传文档",
        description="""
        上传文档到指定课程。
        
        **功能说明：**
        - 支持上传md、txt、pdf、docx等格式文档
        - 自动处理文档内容并索引到Milvus向量数据库
        - 文档会自动分块处理，便于RAG检索
        
        **权限要求：**
        - 仅管理员和教师可以上传文档
        
        **注意事项：**
        - 文件大小限制：50MB
        - 上传后会自动处理，处理状态可在文档详情中查看
        """,
        tags=["文档管理"],
        request=DocumentUploadSerializer,
        responses={
            200: OpenApiResponse(
                description="上传成功",
                response=inline_serializer(
                    name="DocumentUploadResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": DocumentSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="请求参数错误"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="权限不足"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="upload_document"
    )
    def post(self, request):
        """上传文档接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取用户ID
            user_id = request.user.id
            if not user_id:
                return JsonResponse({
                    "success": False,
                    "message": "无法从JWT token中获取用户ID"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 验证请求数据
            serializer = DocumentUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "请求参数验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取验证后的数据
            validated_data = serializer.validated_data
            course_id = validated_data.get("course_id")
            uploaded_file = validated_data.get("file")
            
            # 调用服务层上传文档
            document_service = DocumentService()
            success, message, document = document_service.upload_document(
                user_id=user_id,
                course_id=course_id,
                uploaded_file=uploaded_file
            )
            
            if success and document:
                # 序列化返回数据
                response_data = DocumentSerializer(document).data
                return JsonResponse({
                    "success": True,
                    "message": message,
                    "data": response_data
                })
            else:
                # 根据错误类型返回不同的状态码
                if "权限" in message or "只有" in message:
                    status_code = status.HTTP_403_FORBIDDEN
                else:
                    status_code = status.HTTP_400_BAD_REQUEST
                
                return JsonResponse({
                    "success": False,
                    "message": message
                }, status=status_code)
                
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"上传文档时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentDeleteView(APIView):
    """文档删除视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="删除文档",
        description="""
        删除指定文档（逻辑删除）。
        
        **功能说明：**
        - 仅对MySQL数据库进行逻辑删除
        - Milvus中的向量数据暂不删除（功能待实现）
        
        **权限要求：**
        - 仅管理员和教师可以删除文档
        
        **注意事项：**
        - 删除后文档在列表中不可见，但文件仍保留在服务器
        """,
        tags=["文档管理"],
        responses={
            200: OpenApiResponse(
                description="删除成功",
                response=inline_serializer(
                    name="DocumentDeleteResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="权限不足"),
            404: OpenApiResponse(description="文档不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="delete_document"
    )
    def delete(self, request, document_id):
        """删除文档接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取用户ID
            user_id = request.user.id
            if not user_id:
                return JsonResponse({
                    "success": False,
                    "message": "无法从JWT token中获取用户ID"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 调用服务层删除文档
            document_service = DocumentService()
            success, message = document_service.delete_document(
                user_id=user_id,
                document_id=document_id
            )
            
            if success:
                return JsonResponse({
                    "success": True,
                    "message": message
                })
            else:
                # 根据错误类型返回不同的状态码
                if "权限" in message or "只有" in message:
                    status_code = status.HTTP_403_FORBIDDEN
                elif "不存在" in message:
                    status_code = status.HTTP_404_NOT_FOUND
                else:
                    status_code = status.HTTP_400_BAD_REQUEST
                
                return JsonResponse({
                    "success": False,
                    "message": message
                }, status=status_code)
                
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"删除文档时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentDownloadView(APIView):
    """文档下载视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="下载文档",
        description="""
        下载指定文档文件。
        
        **功能说明：**
        - 所有登录用户都可以下载文档
        - 返回原始文件内容
        
        **注意事项：**
        - 文档必须存在且未被删除
        """,
        tags=["文档管理"],
        responses={
            200: OpenApiResponse(description="下载成功，返回文件内容"),
            401: OpenApiResponse(description="未登录"),
            404: OpenApiResponse(description="文档不存在或文件不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="download_document"
    )
    def get(self, request, document_id):
        """下载文档接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取文档（使用静态方法，避免初始化Milvus）
            document = DocumentService.get_document(document_id)
            
            if not document:
                return JsonResponse({
                    "success": False,
                    "message": "文档不存在"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 获取文件路径（使用静态方法）
            file_path = DocumentService.get_document_file_path(document)
            
            if not file_path or not file_path.exists():
                return JsonResponse({
                    "success": False,
                    "message": "文档文件不存在"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 返回文件响应
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=document.mime_type or 'application/octet-stream'
            )
            # 使用 RFC 5987 格式支持中文文件名，同时提供标准格式作为备用
            from urllib.parse import quote
            encoded_filename = quote(document.file_name, safe='')
            response['Content-Disposition'] = (
                f'attachment; filename="{document.file_name}"; '
                f'filename*=UTF-8\'\'{encoded_filename}'
            )
            
            return response
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"下载文档时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentDetailView(APIView):
    """文档详情视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="查看文档详情",
        description="""
        获取指定文档的详细信息。
        
        **功能说明：**
        - 所有登录用户都可以查看文档详情
        - 返回文档的完整信息，包括处理状态
        
        **注意事项：**
        - 文档必须存在且未被删除
        """,
        tags=["文档管理"],
        responses={
            200: OpenApiResponse(
                description="获取成功",
                response=inline_serializer(
                    name="DocumentDetailResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": DocumentSerializer()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            404: OpenApiResponse(description="文档不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_document_detail"
    )
    def get(self, request, document_id):
        """获取文档详情接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取文档（使用静态方法，避免初始化Milvus）
            document = DocumentService.get_document(document_id)
            
            if not document:
                return JsonResponse({
                    "success": False,
                    "message": "文档不存在"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 序列化返回数据
            response_data = DocumentSerializer(document).data
            
            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": response_data
            })
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取文档详情时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentListView(APIView):
    """文档列表视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="获取文档列表",
        description="""
        获取文档列表，支持按课程筛选。
        
        **功能说明：**
        - 所有登录用户都可以查看文档列表
        - 支持按课程ID筛选
        - 支持分页
        
        **查询参数：**
        - course_id: 课程ID（可选）
        - page: 页码（默认1）
        - page_size: 每页数量（默认20，最大100）
        """,
        tags=["文档管理"],
        parameters=[
            {
                "name": "course_id",
                "in": "query",
                "description": "课程ID",
                "required": False,
                "schema": {"type": "integer"}
            },
            {
                "name": "page",
                "in": "query",
                "description": "页码（默认1）",
                "required": False,
                "schema": {"type": "integer", "default": 1}
            },
            {
                "name": "page_size",
                "in": "query",
                "description": "每页数量（默认20，最大100）",
                "required": False,
                "schema": {"type": "integer", "default": 20, "maximum": 100}
            }
        ],
        responses={
            200: OpenApiResponse(
                description="获取成功",
                response=inline_serializer(
                    name="DocumentListResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": DocumentListSerializer(many=True),
                        "total": serializers.IntegerField(),
                        "page": serializers.IntegerField(),
                        "page_size": serializers.IntegerField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_document_list"
    )
    def get(self, request):
        """获取文档列表接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取查询参数
            course_id = request.GET.get("course_id")
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 20))
            
            # 限制最大数量
            if page_size > 100:
                page_size = 100
            if page_size < 1:
                page_size = 20
            if page < 1:
                page = 1
            
            # 转换course_id为整数（如果提供）
            if course_id:
                try:
                    course_id = int(course_id)
                except (ValueError, TypeError):
                    course_id = None
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 调用服务层获取文档列表（使用静态方法，避免初始化Milvus）
            documents, total = DocumentService.list_documents(
                course_id=course_id,
                limit=page_size,
                offset=offset
            )
            
            # 序列化数据
            documents_data = DocumentListSerializer(documents, many=True).data
            
            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": documents_data,
                "total": total,
                "page": page,
                "page_size": page_size
            })
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取文档列表时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
