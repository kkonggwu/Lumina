from rest_framework import serializers
from .models import QAHistory


class ChatRequestSerializer(serializers.Serializer):
    """
    普通问答请求序列化器
    """
    question = serializers.CharField(
        required=True,
        help_text="用户问题",
        max_length=2000
    )
    session_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="会话ID，用于多轮对话。如果不提供，系统会自动生成",
        max_length=50
    )
    course_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="关联课程ID（可选，普通问答时可为空）"
    )

    def validate_question(self, value):
        """
        验证问题不能为空
        """
        if not value or not value.strip():
            raise serializers.ValidationError("问题不能为空")
        return value.strip()


class ChatResponseSerializer(serializers.ModelSerializer):
    """
    问答响应序列化器
    """
    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )
    
    class Meta:
        model = QAHistory
        fields = [
            'id', 'user_id', 'course_id', 'session_id',
            'question', 'answer', 'context_docs', 'source_documents',
            'prompt_tokens', 'completion_tokens', 'total_tokens',
            'feedback', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_id', 'course_id', 'session_id',
            'answer', 'context_docs', 'source_documents',
            'prompt_tokens', 'completion_tokens', 'total_tokens',
            'created_at'
        ]


class QAHistorySerializer(serializers.ModelSerializer):
    """
    问答历史序列化器（用于查询历史记录）
    """
    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True
    )

    class Meta:
        model = QAHistory
        fields = [
            'id', 'user_id', 'course_id', 'session_id',
            'question', 'answer', 'context_docs', 'source_documents',
            'prompt_tokens', 'completion_tokens', 'total_tokens',
            'feedback', 'created_at'
        ]
        read_only_fields = fields

