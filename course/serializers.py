#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档序列化器
"""
from rest_framework import serializers
from .models import Document, Course


class DocumentSerializer(serializers.ModelSerializer):
    """文档序列化器"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    uploader_name = serializers.CharField(source='uploader.nickname', read_only=True)
    document_status_display = serializers.SerializerMethodField()
    
    def get_document_status_display(self, obj):
        """获取文档状态显示名称"""
        status_choices = dict(obj.DOCUMENT_STATUS_CHOICES)
        return status_choices.get(obj.document_status, '未知')
    
    class Meta:
        model = Document
        fields = [
            'id', 'course', 'course_name', 'uploader', 'uploader_name',
            'file_name', 'stored_path', 'file_size', 'file_type', 'mime_type',
            'document_status', 'document_status_display', 'processing_log',
            'is_deleted', 'uploaded_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'stored_path', 'file_size', 'file_type', 'mime_type',
            'document_status', 'processing_log', 'uploaded_at', 'updated_at'
        ]


class DocumentUploadSerializer(serializers.Serializer):
    """文档上传序列化器"""
    course_id = serializers.IntegerField(required=True, help_text='课程ID')
    file = serializers.FileField(required=True, help_text='上传的文件（支持md、txt等格式）')
    
    def validate_course_id(self, value):
        """验证课程ID是否存在"""
        try:
            course = Course.objects.get(id=value, is_deleted=False)
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError("课程不存在")
    
    def validate_file(self, value):
        """验证文件格式和大小"""
        # 检查文件扩展名
        allowed_extensions = ['.md', '.txt', '.markdown', '.pdf', '.docx']
        file_name = value.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"不支持的文件格式。支持格式: {', '.join(allowed_extensions)}"
            )
        
        # 检查文件大小（限制为50MB）
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("文件大小不能超过50MB")
        
        return value


class DocumentListSerializer(serializers.ModelSerializer):
    """文档列表序列化器（简化版）"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    uploader_name = serializers.CharField(source='uploader.nickname', read_only=True)
    document_status_display = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    def get_document_status_display(self, obj):
        """获取文档状态显示名称"""
        status_choices = dict(obj.DOCUMENT_STATUS_CHOICES)
        return status_choices.get(obj.document_status, '未知')
    
    class Meta:
        model = Document
        fields = [
            'id', 'course_id', 'course_name', 'uploader_id', 'uploader_name',
            'file_name', 'file_size', 'file_size_mb', 'file_type',
            'document_status', 'document_status_display',
            'uploaded_at', 'updated_at'
        ]
    
    def get_file_size_mb(self, obj):
        """计算文件大小（MB）"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0

