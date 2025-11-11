from django.db import models
import json


class QAHistory(models.Model):
    """
    问答历史模型，映射数据库中的qa_history表
    """
    # 反馈常量定义
    NO_FEEDBACK = None
    NEGATIVE = 0
    POSITIVE = 1
    FEEDBACK_CHOICES = (
        (NEGATIVE, '否定'),
        (POSITIVE, '肯定'),
    )

    # 逻辑删除常量定义
    NOT_DELETED = 0
    DELETED = 1
    DELETION_CHOICES = (
        (NOT_DELETED, '正常'),
        (DELETED, '删除'),
    )

    id = models.AutoField(primary_key=True, verbose_name='历史ID')
    user_id = models.IntegerField(verbose_name='用户ID')
    course_id = models.IntegerField(null=True, blank=True, verbose_name='关联课程ID')
    session_id = models.CharField(max_length=50, verbose_name='会话ID')
    question = models.TextField(verbose_name='用户问题')
    answer = models.TextField(verbose_name='系统回答')
    context_docs = models.JSONField(null=True, blank=True, verbose_name='参考文档信息')
    source_documents = models.JSONField(null=True, blank=True, verbose_name='来源文档(JSON格式)')
    prompt_tokens = models.IntegerField(null=True, blank=True, verbose_name='提示令牌数')
    completion_tokens = models.IntegerField(null=True, blank=True, verbose_name='完成令牌数')
    total_tokens = models.IntegerField(null=True, blank=True, verbose_name='总令牌数')
    feedback = models.IntegerField(
        null=True,
        blank=True,
        choices=FEEDBACK_CHOICES,
        verbose_name='用户反馈'
    )
    is_deleted = models.IntegerField(
        choices=DELETION_CHOICES,
        default=NOT_DELETED,
        verbose_name='逻辑删除'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        managed = False  # 不自动创建和管理表
        db_table = 'qa_history'  # 数据库表名
        app_label = 'rag'  # 明确指定应用标签
        verbose_name = '问答历史'
        verbose_name_plural = '问答历史管理'
        ordering = ['-created_at']  # 按创建时间倒序

    def __str__(self):
        return f"QA-{self.id}: {self.question[:50]}..."
