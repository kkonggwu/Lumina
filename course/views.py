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

# ==================== 课程管理视图 ====================

from .services.course_service import CourseService, EnrollmentService
from .serializers import (
    CourseSerializer,
    CourseCreateSerializer,
    CourseUpdateSerializer,
    CourseListSerializer,
    EnrollmentSerializer,
    EnrollmentJoinSerializer,
    EnrollmentListSerializer
)


class CourseListCreateView(APIView):
    """课程列表和创建视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="获取课程列表",
        description="""
        获取课程列表，支持多种筛选条件。
        
        **功能说明：**
        - 所有登录用户都可以查看课程列表
        - 支持按教师ID筛选
        - 支持按状态筛选
        - 支持按是否公开筛选
        - 支持分页
        """,
        tags=["课程管理"],
        parameters=[
            {
                "name": "teacher_id",
                "in": "query",
                "description": "教师ID",
                "required": False,
                "schema": {"type": "integer"}
            },
            {
                "name": "status",
                "in": "query",
                "description": "状态（0-草稿，1-已发布）",
                "required": False,
                "schema": {"type": "integer"}
            },
            {
                "name": "is_public",
                "in": "query",
                "description": "是否公开（true/false）",
                "required": False,
                "schema": {"type": "boolean"}
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
                    name="CourseListResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": CourseListSerializer(many=True),
                        "total": serializers.IntegerField(),
                        "page": serializers.IntegerField(),
                        "page_size": serializers.IntegerField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_course_list"
    )
    def get(self, request):
        """获取课程列表接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取查询参数
            teacher_id = request.GET.get("teacher_id")
            status_param = request.GET.get("status")
            is_public_param = request.GET.get("is_public")
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 20))
            
            # 限制最大数量
            if page_size > 100:
                page_size = 100
            if page_size < 1:
                page_size = 20
            if page < 1:
                page = 1
            
            # 转换参数类型
            if teacher_id:
                try:
                    teacher_id = int(teacher_id)
                except (ValueError, TypeError):
                    teacher_id = None
            
            if status_param:
                try:
                    status_param = int(status_param)
                except (ValueError, TypeError):
                    status_param = None
            
            if is_public_param:
                is_public_param = is_public_param.lower() in ['true', '1', 'yes']
            else:
                is_public_param = None
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 调用服务层获取课程列表
            courses, total = CourseService.list_courses(
                teacher_id=teacher_id,
                status=status_param,
                is_public=is_public_param,
                limit=page_size,
                offset=offset
            )
            
            # 序列化数据
            courses_data = CourseListSerializer(courses, many=True).data
            
            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": courses_data,
                "total": total,
                "page": page,
                "page_size": page_size
            })
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取课程列表时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="创建课程",
        description="""
        创建新课程。
        
        **功能说明：**
        - 只有管理员和教师可以创建课程
        - 系统会自动生成唯一的邀请码
        - 创建者自动成为课程教师
        
        **权限要求：**
        - 仅管理员和教师可以创建课程
        
        **注意事项：**
        - 课程名称必填
        - 邀请码自动生成，无需提供
        """,
        tags=["课程管理"],
        request=CourseCreateSerializer,
        responses={
            200: OpenApiResponse(
                description="创建成功",
                response=inline_serializer(
                    name="CourseCreateResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": CourseSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="请求参数错误"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="权限不足"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="create_course"
    )
    def post(self, request):
        """创建课程接口"""
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
            serializer = CourseCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "请求参数验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取验证后的数据
            validated_data = serializer.validated_data
            
            # 调用服务层创建课程
            success, message, course = CourseService.create_course(
                teacher_id=user_id,
                **validated_data
            )
            
            if success and course:
                # 序列化返回数据
                response_data = CourseSerializer(course).data
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
                "message": f"创建课程时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseDetailUpdateView(APIView):
    """课程详情和更新视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="查看课程详情",
        description="""
        获取指定课程的详细信息。
        
        **功能说明：**
        - 所有登录用户都可以查看课程详情
        - 返回课程的完整信息，包括学生数量
        
        **注意事项：**
        - 课程必须存在且未被删除
        """,
        tags=["课程管理"],
        responses={
            200: OpenApiResponse(
                description="获取成功",
                response=inline_serializer(
                    name="CourseDetailResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": CourseSerializer()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            404: OpenApiResponse(description="课程不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_course_detail"
    )
    def get(self, request, course_id):
        """获取课程详情接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取课程
            course = CourseService.get_course(course_id)
            
            if not course:
                return JsonResponse({
                    "success": False,
                    "message": "课程不存在"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 序列化返回数据
            response_data = CourseSerializer(course).data
            
            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": response_data
            })
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取课程详情时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="更新课程",
        description="""
        更新课程信息。
        
        **功能说明：**
        - 管理员可以更新任何课程
        - 教师只能更新自己创建的课程
        - 可以部分更新，只提供需要修改的字段即可
        
        **权限要求：**
        - 管理员或课程创建教师
        
        **注意事项：**
        - 邀请码不可修改
        - 只能更新自己创建的课程（教师）
        """,
        tags=["课程管理"],
        request=CourseUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="更新成功",
                response=inline_serializer(
                    name="CourseUpdateResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": CourseSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="请求参数错误"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="权限不足"),
            404: OpenApiResponse(description="课程不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="update_course"
    )
    def put(self, request, course_id):
        """更新课程接口"""
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
            serializer = CourseUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "请求参数验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取验证后的数据
            validated_data = serializer.validated_data
            
            # 调用服务层更新课程
            success, message, course = CourseService.update_course(
                user_id=user_id,
                course_id=course_id,
                **validated_data
            )
            
            if success and course:
                # 序列化返回数据
                response_data = CourseSerializer(course).data
                return JsonResponse({
                    "success": True,
                    "message": message,
                    "data": response_data
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
                "message": f"更新课程时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseDeleteView(APIView):
    """课程删除视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="删除课程",
        description="""
        删除课程（逻辑删除）。
        
        **功能说明：**
        - 管理员可以删除任何课程
        - 教师只能删除自己创建的课程
        - 删除后课程在列表中不可见，但数据仍保留
        
        **权限要求：**
        - 管理员或课程创建教师
        
        **注意事项：**
        - 删除后课程在列表中不可见
        - 已选课的学生关系也会被标记为删除
        """,
        tags=["课程管理"],
        responses={
            200: OpenApiResponse(
                description="删除成功",
                response=inline_serializer(
                    name="CourseDeleteResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="权限不足"),
            404: OpenApiResponse(description="课程不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="delete_course"
    )
    def delete(self, request, course_id):
        """删除课程接口"""
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
            
            # 调用服务层删除课程
            success, message = CourseService.delete_course(
                user_id=user_id,
                course_id=course_id
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
                "message": f"删除课程时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# ==================== 选课管理视图 ====================

class EnrollmentJoinView(APIView):
    """加入课程视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="加入课程",
        description="""
        学生通过邀请码加入课程。
        
        **功能说明：**
        - 只有学生可以加入课程
        - 需要提供有效的课程邀请码
        - 课程必须已发布
        - 课程人数未满
        
        **权限要求：**
        - 仅学生可以加入课程
        
        **注意事项：**
        - 不能重复加入同一课程
        - 如果课程人数已满，无法加入
        """,
        tags=["选课管理"],
        request=EnrollmentJoinSerializer,
        responses={
            200: OpenApiResponse(
                description="加入成功",
                response=inline_serializer(
                    name="EnrollmentJoinResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": EnrollmentSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="请求参数错误"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="权限不足"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="join_course"
    )
    def post(self, request):
        """加入课程接口"""
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
            serializer = EnrollmentJoinSerializer(data=request.data)
            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "请求参数验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取验证后的数据
            invite_code = serializer.validated_data.get("invite_code")
            
            # 调用服务层加入课程
            success, message, enrollment = EnrollmentService.join_course_by_invite_code(
                student_id=user_id,
                invite_code=invite_code
            )
            
            if success and enrollment:
                # 序列化返回数据
                response_data = EnrollmentSerializer(enrollment).data
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
                "message": f"加入课程时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnrollmentLeaveView(APIView):
    """退出课程视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="退出课程",
        description="""
        学生退出已加入的课程。
        
        **功能说明：**
        - 只有学生可以退出课程
        - 只能退出自己已加入的课程
        
        **权限要求：**
        - 仅学生可以退出课程
        
        **注意事项：**
        - 退出后无法再通过原邀请码加入（需要重新申请）
        """,
        tags=["选课管理"],
        responses={
            200: OpenApiResponse(
                description="退出成功",
                response=inline_serializer(
                    name="EnrollmentLeaveResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            404: OpenApiResponse(description="未加入该课程"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="leave_course"
    )
    def delete(self, request, course_id):
        """退出课程接口"""
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
            
            # 调用服务层退出课程
            success, message = EnrollmentService.leave_course(
                student_id=user_id,
                course_id=course_id
            )
            
            if success:
                return JsonResponse({
                    "success": True,
                    "message": message
                })
            else:
                # 根据错误类型返回不同的状态码
                if "不存在" in message or "未加入" in message:
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
                "message": f"退出课程时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseStudentsView(APIView):
    """课程学生列表视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="获取课程学生列表",
        description="""
        获取指定课程的学生列表。
        
        **功能说明：**
        - 所有登录用户都可以查看课程学生列表
        - 支持按选课状态筛选
        - 支持分页
        
        **查询参数：**
        - enrollment_status: 选课状态（可选，0-待审核，1-已加入，2-已退出）
        - page: 页码（默认1）
        - page_size: 每页数量（默认50，最大100）
        """,
        tags=["选课管理"],
        parameters=[
            {
                "name": "enrollment_status",
                "in": "query",
                "description": "选课状态（0-待审核，1-已加入，2-已退出）",
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
                "description": "每页数量（默认50，最大100）",
                "required": False,
                "schema": {"type": "integer", "default": 50, "maximum": 100}
            }
        ],
        responses={
            200: OpenApiResponse(
                description="获取成功",
                response=inline_serializer(
                    name="CourseStudentsResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": EnrollmentSerializer(many=True),
                        "total": serializers.IntegerField(),
                        "page": serializers.IntegerField(),
                        "page_size": serializers.IntegerField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            404: OpenApiResponse(description="课程不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_course_students"
    )
    def get(self, request, course_id):
        """获取课程学生列表接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 验证课程是否存在
            course = CourseService.get_course(course_id)
            if not course:
                return JsonResponse({
                    "success": False,
                    "message": "课程不存在"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 获取查询参数
            enrollment_status = request.GET.get("enrollment_status")
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 50))
            
            # 限制最大数量
            if page_size > 100:
                page_size = 100
            if page_size < 1:
                page_size = 50
            if page < 1:
                page = 1
            
            # 转换参数类型
            if enrollment_status:
                try:
                    enrollment_status = int(enrollment_status)
                except (ValueError, TypeError):
                    enrollment_status = None
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 调用服务层获取课程学生列表
            enrollments, total = EnrollmentService.get_course_students(
                course_id=course_id,
                enrollment_status=enrollment_status,
                limit=page_size,
                offset=offset
            )
            
            # 序列化数据
            enrollments_data = EnrollmentSerializer(enrollments, many=True).data
            
            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": enrollments_data,
                "total": total,
                "page": page,
                "page_size": page_size
            })
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取课程学生列表时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudentCoursesView(APIView):
    """学生选课列表视图"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="获取学生选课列表",
        description="""
        获取当前学生的选课列表。
        
        **功能说明：**
        - 学生可以查看自己的选课列表
        - 支持按选课状态筛选
        - 支持分页
        
        **查询参数：**
        - enrollment_status: 选课状态（可选，0-待审核，1-已加入，2-已退出）
        - page: 页码（默认1）
        - page_size: 每页数量（默认20，最大100）
        """,
        tags=["选课管理"],
        parameters=[
            {
                "name": "enrollment_status",
                "in": "query",
                "description": "选课状态（0-待审核，1-已加入，2-已退出）",
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
                    name="StudentCoursesResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": EnrollmentListSerializer(many=True),
                        "total": serializers.IntegerField(),
                        "page": serializers.IntegerField(),
                        "page_size": serializers.IntegerField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_student_courses"
    )
    def get(self, request):
        """获取学生选课列表接口"""
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
            
            # 获取查询参数
            enrollment_status = request.GET.get("enrollment_status")
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 20))
            
            # 限制最大数量
            if page_size > 100:
                page_size = 100
            if page_size < 1:
                page_size = 20
            if page < 1:
                page = 1
            
            # 转换参数类型
            if enrollment_status:
                try:
                    enrollment_status = int(enrollment_status)
                except (ValueError, TypeError):
                    enrollment_status = None
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 调用服务层获取学生选课列表
            enrollments, total = EnrollmentService.get_student_courses(
                student_id=user_id,
                enrollment_status=enrollment_status,
                limit=page_size,
                offset=offset
            )
            
            # 序列化数据
            enrollments_data = EnrollmentListSerializer(enrollments, many=True).data
            
            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": enrollments_data,
                "total": total,
                "page": page,
                "page_size": page_size
            })
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取学生选课列表时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)