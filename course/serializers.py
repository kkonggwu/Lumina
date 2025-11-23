#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档序列化器
"""
from rest_framework import serializers
from .models import Document, Course, Enrollment


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


# ==================== 课程管理序列化器 ====================

class CourseSerializer(serializers.ModelSerializer):
    """课程序列化器"""
    teacher_name = serializers.CharField(source='teacher.nickname', read_only=True)
    teacher_id = serializers.IntegerField(source='teacher.id', read_only=True)
    status_display = serializers.SerializerMethodField()
    semester_display = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    
    def get_status_display(self, obj):
        """获取状态显示名称"""
        status_choices = dict(obj.STATUS_CHOICES)
        return status_choices.get(obj.status, '未知')
    
    def get_semester_display(self, obj):
        """获取学期显示名称"""
        if obj.semester is None:
            return None
        semester_choices = dict(obj.SEMESTER_CHOICES)
        return semester_choices.get(obj.semester, '未知')
    
    def get_student_count(self, obj):
        """获取当前学生数量"""
        from course.models import Enrollment
        return Enrollment.objects.filter(
            course_id=obj.id,
            enrollment_status=1,  # 已加入
            is_deleted=False
        ).count()
    
    class Meta:
        model = Course
        fields = [
            'id', 'teacher_id', 'teacher_name', 'course_name', 'course_description',
            'cover_image', 'invite_code', 'academic_year', 'semester', 'semester_display',
            'max_students', 'is_public', 'status', 'status_display',
            'student_count', 'is_deleted', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'invite_code', 'created_at', 'updated_at', 'student_count'
        ]


class CourseCreateSerializer(serializers.Serializer):
    """课程创建序列化器"""
    course_name = serializers.CharField(required=True, max_length=100, help_text='课程名称')
    course_description = serializers.CharField(required=False, allow_blank=True, help_text='课程描述')
    cover_image = serializers.CharField(required=False, allow_blank=True, max_length=255, help_text='封面图片URL')
    academic_year = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text='学年')
    semester = serializers.IntegerField(required=False, help_text='学期：1-春季，2-秋季')
    max_students = serializers.IntegerField(required=False, default=100, min_value=1, help_text='最大学生数')
    is_public = serializers.BooleanField(required=False, default=False, help_text='是否公开')
    status = serializers.IntegerField(required=False, default=1, help_text='状态：0-草稿，1-已发布')
    
    def validate_semester(self, value):
        """验证学期值"""
        if value is not None and value not in [1, 2]:
            raise serializers.ValidationError("学期值必须是1（春季）或2（秋季）")
        return value
    
    def validate_status(self, value):
        """验证状态值"""
        if value not in [0, 1]:
            raise serializers.ValidationError("状态值必须是0（草稿）或1（已发布）")
        return value


class CourseUpdateSerializer(serializers.Serializer):
    """课程更新序列化器"""
    course_name = serializers.CharField(required=False, max_length=100, help_text='课程名称')
    course_description = serializers.CharField(required=False, allow_blank=True, help_text='课程描述')
    cover_image = serializers.CharField(required=False, allow_blank=True, max_length=255, help_text='封面图片URL')
    academic_year = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text='学年')
    semester = serializers.IntegerField(required=False, help_text='学期：1-春季，2-秋季')
    max_students = serializers.IntegerField(required=False, min_value=1, help_text='最大学生数')
    is_public = serializers.BooleanField(required=False, help_text='是否公开')
    status = serializers.IntegerField(required=False, help_text='状态：0-草稿，1-已发布')
    
    def validate_semester(self, value):
        """验证学期值"""
        if value is not None and value not in [1, 2]:
            raise serializers.ValidationError("学期值必须是1（春季）或2（秋季）")
        return value
    
    def validate_status(self, value):
        """验证状态值"""
        if value is not None and value not in [0, 1]:
            raise serializers.ValidationError("状态值必须是0（草稿）或1（已发布）")
        return value


class CourseListSerializer(serializers.ModelSerializer):
    """课程列表序列化器（简化版）"""
    teacher_name = serializers.CharField(source='teacher.nickname', read_only=True)
    status_display = serializers.SerializerMethodField()
    semester_display = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    
    def get_status_display(self, obj):
        """获取状态显示名称"""
        status_choices = dict(obj.STATUS_CHOICES)
        return status_choices.get(obj.status, '未知')
    
    def get_semester_display(self, obj):
        """获取学期显示名称"""
        if obj.semester is None:
            return None
        semester_choices = dict(obj.SEMESTER_CHOICES)
        return semester_choices.get(obj.semester, '未知')
    
    def get_student_count(self, obj):
        """获取当前学生数量"""
        from course.models import Enrollment
        return Enrollment.objects.filter(
            course_id=obj.id,
            enrollment_status=1,  # 已加入
            is_deleted=False
        ).count()
    
    class Meta:
        model = Course
        fields = [
            'id', 'teacher_id', 'teacher_name', 'course_name', 'course_description',
            'cover_image', 'invite_code', 'academic_year', 'semester', 'semester_display',
            'max_students', 'is_public', 'status', 'status_display',
            'student_count', 'created_at', 'updated_at'
        ]


# ==================== 选课管理序列化器 ====================

class EnrollmentSerializer(serializers.ModelSerializer):
    """选课关系序列化器"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_id = serializers.IntegerField(source='course.id', read_only=True)
    student_name = serializers.CharField(source='student.nickname', read_only=True)
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    enrollment_status_display = serializers.SerializerMethodField()
    
    def get_enrollment_status_display(self, obj):
        """获取选课状态显示名称"""
        status_choices = dict(obj.ENROLLMENT_STATUS_CHOICES)
        return status_choices.get(obj.enrollment_status, '未知')
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'course_id', 'course_name', 'student_id', 'student_name',
            'enrollment_status', 'enrollment_status_display',
            'joined_at', 'is_deleted'
        ]
        read_only_fields = ['id', 'joined_at']


class EnrollmentJoinSerializer(serializers.Serializer):
    """加入课程序列化器"""
    invite_code = serializers.CharField(required=True, max_length=20, help_text='课程邀请码')


class EnrollmentListSerializer(serializers.ModelSerializer):
    """选课列表序列化器（简化版）"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_id = serializers.IntegerField(source='course.id', read_only=True)
    teacher_name = serializers.CharField(source='course.teacher.nickname', read_only=True)
    enrollment_status_display = serializers.SerializerMethodField()
    
    def get_enrollment_status_display(self, obj):
        """获取选课状态显示名称"""
        status_choices = dict(obj.ENROLLMENT_STATUS_CHOICES)
        return status_choices.get(obj.enrollment_status, '未知')
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'course_id', 'course_name', 'teacher_name',
            'enrollment_status', 'enrollment_status_display',
            'joined_at'
        ]

