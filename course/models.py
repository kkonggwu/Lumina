from django.db import models
from django.utils import timezone
from user.models import UserModel


class Course(models.Model):
    """课程表"""
    teacher = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='courses', verbose_name='教师')
    course_name = models.CharField(max_length=100, verbose_name='课程名称')
    course_description = models.TextField(null=True, blank=True, verbose_name='课程描述')
    cover_image = models.CharField(max_length=255, null=True, blank=True, verbose_name='封面图片URL')
    invite_code = models.CharField(max_length=20, unique=True, verbose_name='课程邀请码')
    academic_year = models.CharField(max_length=20, null=True, blank=True, verbose_name='学年')
    SEMESTER_CHOICES = (
        (1, '春季'),
        (2, '秋季'),
    )
    semester = models.IntegerField(choices=SEMESTER_CHOICES, null=True, blank=True, verbose_name='学期')
    max_students = models.IntegerField(default=100, verbose_name='最大学生数')
    is_public = models.BooleanField(default=False, verbose_name='是否公开：0-私有，1-公开')
    STATUS_CHOICES = (
        (0, '草稿'),
        (1, '已发布'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name='状态')
    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        managed = False  # 不自动创建和管理表（表已存在）
        db_table = 'course'  # 数据库表名
        verbose_name = '课程'
        verbose_name_plural = '课程管理'
        indexes = [
            models.Index(fields=['teacher']),
            models.Index(fields=['invite_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.course_name} (教师：{self.teacher.nickname})"


class Enrollment(models.Model):
    """选课关系表"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', verbose_name='课程')
    student = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='enrollments', verbose_name='学生')
    ENROLLMENT_STATUS_CHOICES = (
        (0, '待审核'),
        (1, '已加入'),
        (2, '已退出'),
    )
    enrollment_status = models.IntegerField(choices=ENROLLMENT_STATUS_CHOICES, default=1, verbose_name='选课状态')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')

    class Meta:
        managed = False  # 不自动创建和管理表（表已存在）
        db_table = 'enrollment'  # 数据库表名
        verbose_name = '选课关系'
        verbose_name_plural = '选课管理'
        unique_together = ('course', 'student')
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['course']),
        ]

    def __str__(self):
        return f"{self.student.nickname} - {self.course.course_name}"


class Document(models.Model):
    """文档表"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='documents', verbose_name='课程')
    uploader = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='uploaded_documents', verbose_name='上传者')
    file_name = models.CharField(max_length=255, verbose_name='原始文件名')
    stored_path = models.CharField(max_length=500, verbose_name='存储路径')
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name='文件大小(字节)')
    file_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='文件类型')
    mime_type = models.CharField(max_length=100, null=True, blank=True, verbose_name='MIME类型')
    DOCUMENT_STATUS_CHOICES = (
        (0, '上传中'),
        (1, '处理成功'),
        (2, '处理失败'),
    )
    document_status = models.IntegerField(choices=DOCUMENT_STATUS_CHOICES, default=0, verbose_name='状态')
    processing_log = models.TextField(null=True, blank=True, verbose_name='处理日志')
    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        managed = False  # 不自动创建和管理表（表已存在）
        db_table = 'document'  # 数据库表名
        verbose_name = '文档'
        verbose_name_plural = '文档管理'
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['uploader']),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.course.course_name}"


class Assignment(models.Model):
    """作业表"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments', verbose_name='课程')
    teacher = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='assignments', verbose_name='教师')
    title = models.CharField(max_length=200, verbose_name='作业标题')
    description = models.TextField(null=True, blank=True, verbose_name='作业描述')
    questions = models.JSONField(verbose_name='题目列表(JSON格式)')
    total_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='作业总分')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='截止时间')
    ASSIGNMENT_STATUS_CHOICES = (
        (0, '草稿'),
        (1, '已发布'),
    )
    assignment_status = models.IntegerField(choices=ASSIGNMENT_STATUS_CHOICES, default=0, verbose_name='状态')
    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        managed = False  # 不自动创建和管理表（表已存在）
        db_table = 'assignment'  # 数据库表名
        verbose_name = '作业'
        verbose_name_plural = '作业管理'
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['teacher']),
            models.Index(fields=['end_time']),
        ]

    def __str__(self):
        return f"{self.title} - {self.course.course_name}"


class Submission(models.Model):
    """作业提交表"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', verbose_name='作业')
    student = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='submissions', verbose_name='学生')
    answers = models.JSONField(null=True, blank=True, verbose_name='学生答案(JSON格式)')
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='得分')
    SUBMISSION_STATUS_CHOICES = (
        (0, '未提交'),
        (1, '已提交待批改'),
        (2, '已批改'),
        (3, '已过期'),
    )
    submission_status = models.IntegerField(choices=SUBMISSION_STATUS_CHOICES, default=0, verbose_name='状态')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提交时间')
    graded_at = models.DateTimeField(null=True, blank=True, verbose_name='批改时间')
    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        managed = False  # 不自动创建和管理表（表已存在）
        db_table = 'submission'  # 数据库表名
        verbose_name = '作业提交'
        verbose_name_plural = '作业提交管理'
        unique_together = ('assignment', 'student')
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['assignment']),
            models.Index(fields=['submission_status']),
        ]

    def __str__(self):
        return f"{self.student.nickname} - {self.assignment.title}"


class Grade(models.Model):
    """评分详情表"""
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='grade', verbose_name='提交')
    grading_rubric = models.JSONField(verbose_name='评分细则(JSON格式)')
    overall_comment = models.TextField(null=True, blank=True, verbose_name='总体评语')
    voice_feedback_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='语音评语路径')
    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        managed = False  # 不自动创建和管理表（表已存在）
        db_table = 'grade'  # 数据库表名
        verbose_name = '评分详情'
        verbose_name_plural = '评分管理'

    def __str__(self):
        return f"评分：{self.submission.student.nickname} - {self.submission.assignment.title}"
