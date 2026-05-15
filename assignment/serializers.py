#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业管理序列化器
"""
from rest_framework import serializers
from course.models import Assignment, Submission, Grade


ALLOWED_QUESTION_TYPES = {"essay", "short_answer", "python", "sql", "report"}


def validate_question_payload(value):
    """Validate assignment question JSON, especially executable code tests."""
    if not value:
        raise serializers.ValidationError("题目列表不能为空")

    for i, q in enumerate(value):
        if 'id' not in q:
            raise serializers.ValidationError(f"第 {i+1} 题缺少 id 字段")
        if 'content' not in q:
            raise serializers.ValidationError(f"第 {i+1} 题缺少 content 字段")
        if 'score' not in q:
            raise serializers.ValidationError(f"第 {i+1} 题缺少 score 字段")
        if 'standard_answer' not in q:
            raise serializers.ValidationError(f"第 {i+1} 题缺少 standard_answer 字段")

        question_type = q.get("question_type", "essay")
        if question_type not in ALLOWED_QUESTION_TYPES:
            raise serializers.ValidationError(
                f"第 {i+1} 题 question_type 非法: {question_type}，"
                f"仅支持 {', '.join(sorted(ALLOWED_QUESTION_TYPES))}"
            )

        if question_type == "python":
            _validate_python_cases(i, q.get("test_cases"))
        elif question_type == "sql":
            _validate_sql_cases(i, q.get("test_cases"))
        elif question_type == "report":
            rubric = q.get("grading_rubric")
            _validate_report_rubric(i, rubric)
    return value


def _validate_python_cases(question_index, test_cases):
    if not isinstance(test_cases, list) or not test_cases:
        raise serializers.ValidationError(
            f"第 {question_index + 1} 题为 python 类型，必须提供非空 test_cases 列表"
        )
    for case_index, case in enumerate(test_cases):
        if not isinstance(case, dict):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {case_index + 1} 个测试用例必须为对象"
            )
        if not case.get("function_name"):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {case_index + 1} 个测试用例缺少 function_name"
            )
        if "input" not in case:
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {case_index + 1} 个测试用例缺少 input"
            )
        if "expected" not in case and "output" not in case:
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {case_index + 1} 个测试用例缺少 expected"
            )


def _validate_sql_cases(question_index, test_cases):
    if not isinstance(test_cases, list) or not test_cases:
        raise serializers.ValidationError(
            f"第 {question_index + 1} 题为 sql 类型，必须提供非空 test_cases 列表"
        )
    for case_index, case in enumerate(test_cases):
        if not isinstance(case, dict):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {case_index + 1} 个测试用例必须为对象"
            )
        if not case.get("setup_sql") and not case.get("input"):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {case_index + 1} 个测试用例缺少 setup_sql"
            )
        if "expected_rows" not in case and "expected" not in case and "output" not in case:
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {case_index + 1} 个测试用例缺少 expected_rows"
            )


def _validate_report_rubric(question_index, rubric):
    """
    校验报告题评分细则。

    兼容两种格式：
    - str: 教师自由文本评分说明
    - dict: 结构化 Rubric，形如 {"dimensions": [{id, name, weight, criteria, required_evidence}]}
    """
    if rubric is None or isinstance(rubric, str):
        return

    if not isinstance(rubric, dict):
        raise serializers.ValidationError(
            f"第 {question_index + 1} 题 grading_rubric 格式非法，须为字符串或对象"
        )

    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise serializers.ValidationError(
            f"第 {question_index + 1} 题 report 类型的结构化 grading_rubric 必须包含非空 dimensions 列表"
        )

    total_weight = 0.0
    seen_ids = set()
    for dimension_index, dimension in enumerate(dimensions):
        if not isinstance(dimension, dict):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {dimension_index + 1} 个评分维度必须为对象"
            )

        dim_id = dimension.get("id")
        name = dimension.get("name")
        weight = dimension.get("weight")
        criteria = dimension.get("criteria")
        required_evidence = dimension.get("required_evidence", [])

        if not dim_id or not isinstance(dim_id, str):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题第 {dimension_index + 1} 个评分维度缺少字符串 id"
            )
        if dim_id in seen_ids:
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题评分维度 id 重复: {dim_id}"
            )
        seen_ids.add(dim_id)

        if not name or not isinstance(name, str):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题评分维度 {dim_id} 缺少字符串 name"
            )

        if not isinstance(weight, (int, float)) or weight <= 0:
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题评分维度 {dim_id} 的 weight 必须为正数"
            )
        total_weight += float(weight)

        if not isinstance(criteria, (str, list)) or not criteria:
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题评分维度 {dim_id} 的 criteria 必须为非空字符串或列表"
            )
        if isinstance(criteria, list) and not all(isinstance(item, str) and item.strip() for item in criteria):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题评分维度 {dim_id} 的 criteria 列表元素必须为非空字符串"
            )

        if not isinstance(required_evidence, (str, list)):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题评分维度 {dim_id} 的 required_evidence 必须为字符串或列表"
            )
        if isinstance(required_evidence, list) and not all(isinstance(item, str) for item in required_evidence):
            raise serializers.ValidationError(
                f"第 {question_index + 1} 题评分维度 {dim_id} 的 required_evidence 列表元素必须为字符串"
            )

    if not (0.99 <= total_weight <= 1.01 or 99.0 <= total_weight <= 101.0):
        raise serializers.ValidationError(
            f"第 {question_index + 1} 题 grading_rubric 权重和必须为 1 或 100，当前为 {round(total_weight, 4)}"
        )


# ==================== 作业 CRUD ====================

class AssignmentCreateSerializer(serializers.Serializer):
    """创建作业请求校验"""
    course_id = serializers.IntegerField(required=True, help_text='课程ID')
    title = serializers.CharField(required=True, max_length=200, help_text='作业标题')
    description = serializers.CharField(required=False, allow_blank=True, help_text='作业描述')
    questions = serializers.ListField(
        child=serializers.DictField(), required=True, help_text='题目列表(JSON数组)'
    )
    total_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=True, help_text='作业总分')
    start_time = serializers.DateTimeField(required=True, help_text='开始时间')
    end_time = serializers.DateTimeField(required=True, help_text='截止时间')

    def validate_questions(self, value):
        return validate_question_payload(value)

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("开始时间必须早于截止时间")
        return data


class AssignmentUpdateSerializer(serializers.Serializer):
    """更新作业请求校验（所有字段可选）"""
    title = serializers.CharField(required=False, max_length=200, help_text='作业标题')
    description = serializers.CharField(required=False, allow_blank=True, help_text='作业描述')
    questions = serializers.ListField(
        child=serializers.DictField(), required=False, help_text='题目列表'
    )
    total_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, help_text='作业总分')
    start_time = serializers.DateTimeField(required=False, help_text='开始时间')
    end_time = serializers.DateTimeField(required=False, help_text='截止时间')

    def validate_questions(self, value):
        return validate_question_payload(value)


class AssignmentDetailSerializer(serializers.ModelSerializer):
    """作业详情响应"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.nickname', read_only=True)
    status_display = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return dict(obj.ASSIGNMENT_STATUS_CHOICES).get(obj.assignment_status, '未知')

    class Meta:
        model = Assignment
        fields = [
            'id', 'course_id', 'course_name', 'teacher_id', 'teacher_name',
            'title', 'description', 'questions', 'total_score',
            'start_time', 'end_time', 'assignment_status', 'status_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssignmentListSerializer(serializers.ModelSerializer):
    """作业列表响应（简化版，不含题目详情）"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.nickname', read_only=True)
    status_display = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return dict(obj.ASSIGNMENT_STATUS_CHOICES).get(obj.assignment_status, '未知')

    def get_question_count(self, obj):
        questions = obj.questions or []
        return len(questions)

    def get_submission_count(self, obj):
        return Submission.objects.filter(
            assignment=obj, is_deleted=False, submission_status__gte=1
        ).count()

    class Meta:
        model = Assignment
        fields = [
            'id', 'course_id', 'course_name', 'teacher_id', 'teacher_name',
            'title', 'description', 'total_score',
            'start_time', 'end_time', 'assignment_status', 'status_display',
            'question_count', 'submission_count',
            'created_at', 'updated_at',
        ]


# ==================== 提交与判题 ====================

class SubmitAnswersSerializer(serializers.Serializer):
    """学生提交答案请求校验"""
    answers = serializers.DictField(
        child=serializers.JSONField(),
        required=True,
        help_text='答案字典，key 为题目 ID 字符串，value 为答案内容'
    )

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("答案不能为空")
        return value


class SubmissionListSerializer(serializers.ModelSerializer):
    """提交列表响应（教师查看用）"""
    student_name = serializers.CharField(source='student.nickname', read_only=True)
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    status_display = serializers.SerializerMethodField()
    has_grade = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return dict(obj.SUBMISSION_STATUS_CHOICES).get(obj.submission_status, '未知')

    def get_has_grade(self, obj):
        return hasattr(obj, 'grade') and obj.grade is not None

    class Meta:
        model = Submission
        fields = [
            'id', 'student_id', 'student_name',
            'total_score', 'submission_status', 'status_display',
            'has_grade', 'submitted_at', 'graded_at',
        ]


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """提交详情 + 成绩响应（学生查看用）"""
    student_name = serializers.CharField(source='student.nickname', read_only=True)
    status_display = serializers.SerializerMethodField()
    grade_info = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return dict(obj.SUBMISSION_STATUS_CHOICES).get(obj.submission_status, '未知')

    def get_grade_info(self, obj):
        try:
            grade = obj.grade
        except Grade.DoesNotExist:
            return None
        if not grade or grade.is_deleted:
            return None
        return {
            'grading_rubric': grade.grading_rubric,
            'overall_comment': grade.overall_comment,
            'created_at': grade.created_at.isoformat() if grade.created_at else None,
        }

    class Meta:
        model = Submission
        fields = [
            'id', 'assignment_id', 'student_id', 'student_name',
            'answers', 'total_score', 'submission_status', 'status_display',
            'submitted_at', 'graded_at', 'grade_info',
        ]


# ==================== 教师人工判题 ====================


class ManualGradeSerializer(serializers.Serializer):
    """
    教师人工评分请求校验

    - total_score: 本次评分的总分
    - grading_rubric: 评分细则（JSON），结构与 Grade.grading_rubric 保持一致，由前端自由组织
    - overall_comment: 总体评语
    """

    total_score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=True,
        help_text='本次评分总分',
    )
    grading_rubric = serializers.JSONField(
        required=False,
        help_text='评分细则(JSON，可选)',
    )
    overall_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='总体评语',
    )


class QuestionKeypointsUpdateSerializer(serializers.Serializer):
    """
    更新题目关键点的请求体

    只关心 keypoints 字段，question_id 从 URL 传递。
    """

    keypoints = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=True,
        help_text='关键点列表，每个元素为一个关键点文本',
    )
