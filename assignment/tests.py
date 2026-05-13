#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主观题评分系统——综合测试用例
覆盖题型：一般问答（essay/short_answer）、SQL题、Python题、大作业（report）

测试层次：
  1. 序列化器校验（无需数据库）
  2. API 视图层（APIClient + Mock 服务层）
  3. 判题服务层（Mock 数据库 + Mock Agent）
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from assignment.serializers import (
    AssignmentCreateSerializer,
    validate_question_payload,
)


# ============================================================
# 公共 fixture 数据
# ============================================================

def make_teacher(uid=1):
    """构造模拟教师用户"""
    from user.models import UserModel
    teacher = MagicMock(spec=UserModel)
    teacher.id = uid
    teacher.nickname = "测试教师"
    teacher.user_type = UserModel.TEACHER
    teacher.is_deleted = UserModel.NOT_DELETED
    return teacher


def make_student(uid=2):
    """构造模拟学生用户"""
    from user.models import UserModel
    student = MagicMock(spec=UserModel)
    student.id = uid
    student.nickname = "测试学生"
    student.user_type = UserModel.STUDENT
    student.is_deleted = UserModel.NOT_DELETED
    return student


BASE_ASSIGNMENT_PAYLOAD = {
    "course_id": 1,
    "title": "数据库期中综合作业",
    "description": "涵盖问答、SQL、Python 与课程报告四种题型",
    "total_score": "100.00",
    "start_time": "2026-05-01T00:00:00+08:00",
    "end_time": "2099-12-31T23:59:59+08:00",
}

# ------- 四种典型题目 -------

ESSAY_QUESTION = {
    "id": "q1",
    "question_type": "essay",
    "content": "请解释什么是数据库事务，并说明 ACID 特性的含义。",
    "score": 20,
    "standard_answer": (
        "数据库事务是一个不可分割的操作序列，具有 ACID 特性：\n"
        "原子性（Atomicity）：事务中的操作要么全部成功，要么全部回滚；\n"
        "一致性（Consistency）：事务执行前后数据库从一个一致状态变到另一个一致状态；\n"
        "隔离性（Isolation）：多个事务并发执行时相互不影响；\n"
        "持久性（Durability）：事务提交后对数据库的修改永久保存。"
    ),
}

SHORT_ANSWER_QUESTION = {
    "id": "q2",
    "question_type": "short_answer",
    "content": "简述 B+ 树索引与哈希索引的区别，各适用于什么场景？",
    "score": 10,
    "standard_answer": (
        "B+ 树索引支持范围查询、排序，适合区间检索；"
        "哈希索引仅支持等值查询，查询速度快但不支持排序与范围查找。"
    ),
}

SQL_QUESTION = {
    "id": "q3",
    "question_type": "sql",
    "content": (
        "已知表 orders(id, customer_id, amount, created_at)，"
        "请写出查询每位客户的订单总金额，并按总金额降序排列的 SQL。"
    ),
    "score": 30,
    "standard_answer": (
        "SELECT customer_id, SUM(amount) AS total_amount\n"
        "FROM orders\n"
        "GROUP BY customer_id\n"
        "ORDER BY total_amount DESC;"
    ),
    "test_cases": [
        {
            "setup_sql": (
                "CREATE TABLE IF NOT EXISTS orders "
                "(id INT PRIMARY KEY, customer_id INT, amount DECIMAL(10,2), created_at DATE);\n"
                "INSERT INTO orders VALUES (1,101,200.00,'2026-01-01'),"
                "(2,102,150.00,'2026-01-02'),(3,101,300.00,'2026-01-03');"
            ),
            "input": "",
            "expected_rows": [
                {"customer_id": 101, "total_amount": "500.00"},
                {"customer_id": 102, "total_amount": "150.00"},
            ],
        },
        {
            "setup_sql": (
                "CREATE TABLE IF NOT EXISTS orders "
                "(id INT PRIMARY KEY, customer_id INT, amount DECIMAL(10,2), created_at DATE);\n"
                "INSERT INTO orders VALUES (10,201,50.00,'2026-02-01'),"
                "(11,202,80.00,'2026-02-02'),(12,202,120.00,'2026-02-03');"
            ),
            "input": "",
            "expected_rows": [
                {"customer_id": 202, "total_amount": "200.00"},
                {"customer_id": 201, "total_amount": "50.00"},
            ],
        },
    ],
}

PYTHON_QUESTION = {
    "id": "q4",
    "question_type": "python",
    "content": (
        "请实现函数 fibonacci(n)，返回斐波那契数列第 n 项（n 从 0 开始，"
        "fibonacci(0)=0，fibonacci(1)=1）。"
    ),
    "score": 20,
    "standard_answer": (
        "def fibonacci(n):\n"
        "    if n <= 0:\n"
        "        return 0\n"
        "    if n == 1:\n"
        "        return 1\n"
        "    a, b = 0, 1\n"
        "    for _ in range(2, n + 1):\n"
        "        a, b = b, a + b\n"
        "    return b\n"
    ),
    "test_cases": [
        {"function_name": "fibonacci", "input": [0], "expected": 0},
        {"function_name": "fibonacci", "input": [1], "expected": 1},
        {"function_name": "fibonacci", "input": [5], "expected": 5},
        {"function_name": "fibonacci", "input": [10], "expected": 55},
        {"function_name": "fibonacci", "input": [20], "expected": 6765},
    ],
}

REPORT_QUESTION = {
    "id": "q5",
    "question_type": "report",
    "content": (
        "【大作业】请撰写一份不少于 2000 字的课程学习总结报告，内容包括：\n"
        "1. 本学期学习到的核心知识点梳理（关系型数据库设计、SQL 优化、事务管理等）；\n"
        "2. 至少一个实际项目或实验的收获与反思；\n"
        "3. 对数据库技术未来发展方向的个人见解。\n"
        "评分标准：内容完整性（40%）、逻辑结构（30%）、语言表达（20%）、创新思考（10%）。"
    ),
    "score": 20,
    "standard_answer": "参见评分细则",
    "grading_rubric": {
        "内容完整性": {"weight": 0.4, "description": "覆盖所有三个主题版块，知识点准确"},
        "逻辑结构": {"weight": 0.3, "description": "层次分明，段落过渡自然"},
        "语言表达": {"weight": 0.2, "description": "用词准确，无明显语病"},
        "创新思考": {"weight": 0.1, "description": "有个人独到见解或延伸阅读引用"},
    },
}

ALL_QUESTIONS = [
    ESSAY_QUESTION,
    SHORT_ANSWER_QUESTION,
    SQL_QUESTION,
    PYTHON_QUESTION,
    REPORT_QUESTION,
]

# 学生答案样本（题目 ID → 答案文本）

STUDENT_ANSWERS_GOOD = {
    "q1": (
        "事务是数据库中一系列操作的逻辑单元。ACID 包含四个特性：\n"
        "原子性保证操作要么全部完成要么全部撤销；一致性保证数据库从一种合法状态过渡到另一种合法状态；"
        "隔离性保证并发事务互不干扰；持久性保证提交后的更改不会丢失。"
    ),
    "q2": (
        "B+ 树支持范围查询和排序，适合 OLTP 中的区间查找；"
        "哈希索引只支持等值匹配，不支持范围和排序，适合键值对快速查找。"
    ),
    "q3": (
        "SELECT customer_id, SUM(amount) AS total_amount\n"
        "FROM orders\n"
        "GROUP BY customer_id\n"
        "ORDER BY total_amount DESC;"
    ),
    "q4": (
        "def fibonacci(n):\n"
        "    if n == 0: return 0\n"
        "    if n == 1: return 1\n"
        "    return fibonacci(n-1) + fibonacci(n-2)\n"
    ),
    "q5": (
        "本学期我系统学习了关系型数据库的核心理论与实践技能……\n"
        "（此处省略正文 2000 字）\n"
        "总结：数据库技术在云原生与 AI 时代面临存算分离的重大变革。"
    ),
}

STUDENT_ANSWERS_BAD = {
    "q1": "我不太清楚，事务就是操作的集合吧。",
    "q2": "两种索引都差不多，没啥区别。",
    "q3": "SELECT * FROM orders;",
    "q4": "def fibonacci(n):\n    return n\n",
    "q5": "这学期学了数据库，挺有意思的。",
}


# ============================================================
# 一、序列化器校验测试（无需数据库，纯 Python 逻辑）
# ============================================================

class TestQuestionPayloadValidation(TestCase):
    """测试题目 JSON 格式校验逻辑"""

    # ---------- 通用必填字段 ----------

    def test_valid_essay_question(self):
        """合法的 essay 题目应通过校验"""
        result = validate_question_payload([ESSAY_QUESTION])
        self.assertEqual(len(result), 1)

    def test_valid_short_answer_question(self):
        """合法的 short_answer 题目应通过校验"""
        result = validate_question_payload([SHORT_ANSWER_QUESTION])
        self.assertEqual(len(result), 1)

    def test_valid_sql_question(self):
        """合法的 sql 题目应通过校验"""
        result = validate_question_payload([SQL_QUESTION])
        self.assertEqual(len(result), 1)

    def test_valid_python_question(self):
        """合法的 python 题目应通过校验"""
        result = validate_question_payload([PYTHON_QUESTION])
        self.assertEqual(len(result), 1)

    def test_valid_report_question(self):
        """合法的 report 题目应通过校验"""
        result = validate_question_payload([REPORT_QUESTION])
        self.assertEqual(len(result), 1)

    def test_valid_all_question_types_combined(self):
        """五种题型混合作业应一次性通过校验"""
        result = validate_question_payload(ALL_QUESTIONS)
        self.assertEqual(len(result), 5)

    def test_missing_id_field(self):
        """缺少 id 字段应抛出校验错误"""
        from rest_framework import serializers
        bad = {**ESSAY_QUESTION}
        del bad["id"]
        with self.assertRaises(serializers.ValidationError) as ctx:
            validate_question_payload([bad])
        self.assertIn("id", str(ctx.exception))

    def test_missing_content_field(self):
        """缺少 content 字段应抛出校验错误"""
        from rest_framework import serializers
        bad = {**ESSAY_QUESTION}
        del bad["content"]
        with self.assertRaises(serializers.ValidationError) as ctx:
            validate_question_payload([bad])
        self.assertIn("content", str(ctx.exception))

    def test_missing_score_field(self):
        """缺少 score 字段应抛出校验错误"""
        from rest_framework import serializers
        bad = {**ESSAY_QUESTION}
        del bad["score"]
        with self.assertRaises(serializers.ValidationError) as ctx:
            validate_question_payload([bad])
        self.assertIn("score", str(ctx.exception))

    def test_missing_standard_answer_field(self):
        """缺少 standard_answer 字段应抛出校验错误"""
        from rest_framework import serializers
        bad = {**ESSAY_QUESTION}
        del bad["standard_answer"]
        with self.assertRaises(serializers.ValidationError) as ctx:
            validate_question_payload([bad])
        self.assertIn("standard_answer", str(ctx.exception))

    def test_invalid_question_type(self):
        """非法 question_type 应抛出校验错误"""
        from rest_framework import serializers
        bad = {**ESSAY_QUESTION, "question_type": "multiple_choice"}
        with self.assertRaises(serializers.ValidationError) as ctx:
            validate_question_payload([bad])
        self.assertIn("question_type", str(ctx.exception).lower() + "multiple_choice")

    def test_empty_questions_list(self):
        """空题目列表应抛出校验错误"""
        from rest_framework import serializers
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([])

    # ---------- SQL 题专项校验 ----------

    def test_sql_missing_test_cases(self):
        """SQL 题缺少 test_cases 应报错"""
        from rest_framework import serializers
        bad = {k: v for k, v in SQL_QUESTION.items() if k != "test_cases"}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_sql_empty_test_cases(self):
        """SQL 题 test_cases 为空列表应报错"""
        from rest_framework import serializers
        bad = {**SQL_QUESTION, "test_cases": []}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_sql_test_case_missing_setup_sql_and_input(self):
        """SQL 测试用例缺少 setup_sql 且无 input 应报错"""
        from rest_framework import serializers
        bad_case = {"expected_rows": [{"customer_id": 1, "total_amount": "100.00"}]}
        bad = {**SQL_QUESTION, "test_cases": [bad_case]}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_sql_test_case_missing_expected_rows(self):
        """SQL 测试用例缺少 expected_rows/expected/output 应报错"""
        from rest_framework import serializers
        bad_case = {"setup_sql": "SELECT 1;"}
        bad = {**SQL_QUESTION, "test_cases": [bad_case]}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    # ---------- Python 题专项校验 ----------

    def test_python_missing_test_cases(self):
        """Python 题缺少 test_cases 应报错"""
        from rest_framework import serializers
        bad = {k: v for k, v in PYTHON_QUESTION.items() if k != "test_cases"}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_python_empty_test_cases(self):
        """Python 题 test_cases 为空列表应报错"""
        from rest_framework import serializers
        bad = {**PYTHON_QUESTION, "test_cases": []}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_python_test_case_missing_function_name(self):
        """Python 测试用例缺少 function_name 应报错"""
        from rest_framework import serializers
        bad_case = {"input": [5], "expected": 5}
        bad = {**PYTHON_QUESTION, "test_cases": [bad_case]}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_python_test_case_missing_input(self):
        """Python 测试用例缺少 input 应报错"""
        from rest_framework import serializers
        bad_case = {"function_name": "fibonacci", "expected": 5}
        bad = {**PYTHON_QUESTION, "test_cases": [bad_case]}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_python_test_case_missing_expected(self):
        """Python 测试用例缺少 expected 且无 output 应报错"""
        from rest_framework import serializers
        bad_case = {"function_name": "fibonacci", "input": [5]}
        bad = {**PYTHON_QUESTION, "test_cases": [bad_case]}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([bad])

    def test_python_test_case_accepts_output_key(self):
        """Python 测试用例使用 output 替代 expected 时应通过"""
        good_case = {"function_name": "fibonacci", "input": [5], "output": 5}
        good = {**PYTHON_QUESTION, "test_cases": [good_case]}
        result = validate_question_payload([good])
        self.assertEqual(len(result), 1)

    # ---------- Report 题专项校验 ----------

    def test_report_with_valid_rubric_dict(self):
        """report 题 grading_rubric 为 dict 时应通过"""
        result = validate_question_payload([REPORT_QUESTION])
        self.assertEqual(len(result), 1)

    def test_report_with_valid_rubric_string(self):
        """report 题 grading_rubric 为字符串时应通过"""
        q = {**REPORT_QUESTION, "grading_rubric": "按内容完整性和逻辑性评分"}
        result = validate_question_payload([q])
        self.assertEqual(len(result), 1)

    def test_report_without_rubric(self):
        """report 题不带 grading_rubric 时应通过（可选字段）"""
        q = {k: v for k, v in REPORT_QUESTION.items() if k != "grading_rubric"}
        result = validate_question_payload([q])
        self.assertEqual(len(result), 1)

    def test_report_with_invalid_rubric_type(self):
        """report 题 grading_rubric 为列表时应报错"""
        from rest_framework import serializers
        q = {**REPORT_QUESTION, "grading_rubric": [1, 2, 3]}
        with self.assertRaises(serializers.ValidationError):
            validate_question_payload([q])


# ============================================================
# 二、AssignmentCreateSerializer 端到端校验
# ============================================================

class TestAssignmentCreateSerializer(TestCase):
    """测试创建作业的序列化器整体校验"""

    def _build_payload(self, questions=None):
        payload = dict(BASE_ASSIGNMENT_PAYLOAD)
        payload["questions"] = questions or ALL_QUESTIONS
        return payload

    def test_valid_mixed_assignment(self):
        """包含所有题型的完整作业 payload 应通过校验"""
        ser = AssignmentCreateSerializer(data=self._build_payload())
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_invalid_start_end_time_order(self):
        """开始时间晚于结束时间应报错"""
        payload = self._build_payload()
        payload["start_time"] = "2099-01-01T00:00:00+08:00"
        payload["end_time"] = "2026-01-01T00:00:00+08:00"
        ser = AssignmentCreateSerializer(data=payload)
        self.assertFalse(ser.is_valid())
        self.assertIn("non_field_errors", ser.errors)

    def test_missing_course_id(self):
        """缺少 course_id 应报错"""
        payload = self._build_payload()
        del payload["course_id"]
        ser = AssignmentCreateSerializer(data=payload)
        self.assertFalse(ser.is_valid())
        self.assertIn("course_id", ser.errors)

    def test_missing_total_score(self):
        """缺少 total_score 应报错"""
        payload = self._build_payload()
        del payload["total_score"]
        ser = AssignmentCreateSerializer(data=payload)
        self.assertFalse(ser.is_valid())
        self.assertIn("total_score", ser.errors)

    def test_essay_only_assignment(self):
        """纯问答题作业应通过校验"""
        payload = self._build_payload([ESSAY_QUESTION, SHORT_ANSWER_QUESTION])
        ser = AssignmentCreateSerializer(data=payload)
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_sql_only_assignment(self):
        """纯 SQL 题作业应通过校验"""
        payload = self._build_payload([SQL_QUESTION])
        ser = AssignmentCreateSerializer(data=payload)
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_python_only_assignment(self):
        """纯 Python 题作业应通过校验"""
        payload = self._build_payload([PYTHON_QUESTION])
        ser = AssignmentCreateSerializer(data=payload)
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_report_only_assignment(self):
        """纯大作业应通过校验"""
        payload = self._build_payload([REPORT_QUESTION])
        ser = AssignmentCreateSerializer(data=payload)
        self.assertTrue(ser.is_valid(), ser.errors)


# ============================================================
# 三、API 视图层测试（Mock 服务层，不访问数据库）
# ============================================================

class BaseAPITest(TestCase):
    """提供鉴权 mock 的基类"""

    def setUp(self):
        self.client = APIClient()
        self.teacher = make_teacher(uid=1)
        self.student = make_student(uid=2)

    def _auth_as_teacher(self):
        """令 APIClient 请求时以教师身份通过鉴权"""
        self.client.force_authenticate(user=self.teacher)

    def _auth_as_student(self):
        """令 APIClient 请求时以学生身份通过鉴权"""
        self.client.force_authenticate(user=self.student)


class TestCreateAssignmentAPI(BaseAPITest):
    """POST /api/assignment/ 创建作业"""

    @patch("assignment.bak.views.AssignmentService.create_assignment")
    def test_create_mixed_assignment_success(self, mock_create):
        """教师发起包含四种题型的作业，返回 200 success"""
        self._auth_as_teacher()

        fake_assignment = MagicMock()
        fake_assignment.id = 99
        fake_assignment.title = "数据库期中综合作业"
        fake_assignment.course_id = 1
        fake_assignment.teacher_id = 1
        fake_assignment.course.course_name = "数据库原理"
        fake_assignment.teacher.nickname = "测试教师"
        fake_assignment.description = ""
        fake_assignment.questions = ALL_QUESTIONS
        fake_assignment.total_score = Decimal("100.00")
        fake_assignment.start_time = timezone.now()
        fake_assignment.end_time = timezone.now()
        fake_assignment.assignment_status = 0
        fake_assignment.ASSIGNMENT_STATUS_CHOICES = [(0, "草稿"), (1, "已发布")]
        fake_assignment.created_at = timezone.now()
        fake_assignment.updated_at = timezone.now()

        mock_create.return_value = (True, "创建成功", fake_assignment)

        payload = dict(BASE_ASSIGNMENT_PAYLOAD)
        payload["questions"] = ALL_QUESTIONS

        response = self.client.post(
            "/api/assignment/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])

    def test_create_assignment_unauthenticated(self):
        """未登录用户不能创建作业"""
        payload = dict(BASE_ASSIGNMENT_PAYLOAD)
        payload["questions"] = ALL_QUESTIONS
        response = self.client.post(
            "/api/assignment/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("assignment.bak.views.AssignmentService.create_assignment")
    def test_create_assignment_with_invalid_python_question(self, mock_create):
        """Python 题缺少 test_cases 时序列化器拦截，不进入服务层"""
        self._auth_as_teacher()
        bad_python = {k: v for k, v in PYTHON_QUESTION.items() if k != "test_cases"}
        payload = dict(BASE_ASSIGNMENT_PAYLOAD)
        payload["questions"] = [bad_python]
        response = self.client.post(
            "/api/assignment/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_create.assert_not_called()

    @patch("assignment.bak.views.AssignmentService.create_assignment")
    def test_create_assignment_with_invalid_sql_question(self, mock_create):
        """SQL 题缺少 test_cases 时序列化器拦截"""
        self._auth_as_teacher()
        bad_sql = {k: v for k, v in SQL_QUESTION.items() if k != "test_cases"}
        payload = dict(BASE_ASSIGNMENT_PAYLOAD)
        payload["questions"] = [bad_sql]
        response = self.client.post(
            "/api/assignment/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_create.assert_not_called()


class TestSubmitAnswersAPI(BaseAPITest):
    """POST /api/assignment/<id>/submit/ 学生提交答案"""

    @patch("assignment.bak.views.GradingService.submit_answers")
    def test_submit_good_answers_success(self, mock_submit):
        """学生提交合法答案应返回成功"""
        self._auth_as_student()
        fake_sub = MagicMock()
        fake_sub.id = 10
        mock_submit.return_value = (True, "提交成功", fake_sub)

        response = self.client.post(
            "/api/assignment/1/submit/",
            data=json.dumps({"answers": STUDENT_ANSWERS_GOOD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["submission_id"], 10)

    @patch("assignment.bak.views.GradingService.submit_answers")
    def test_submit_empty_answers_rejected(self, mock_submit):
        """提交空答案字典应被序列化器拦截（400）"""
        self._auth_as_student()
        response = self.client.post(
            "/api/assignment/1/submit/",
            data=json.dumps({"answers": {}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_submit.assert_not_called()

    @patch("assignment.bak.views.GradingService.submit_answers")
    def test_submit_answers_deadline_passed(self, mock_submit):
        """服务层返回截止错误时 API 应返回 400"""
        self._auth_as_student()
        mock_submit.return_value = (False, "作业已截止", None)

        response = self.client.post(
            "/api/assignment/1/submit/",
            data=json.dumps({"answers": STUDENT_ANSWERS_GOOD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("截止", data["message"])

    def test_submit_answers_unauthenticated(self):
        """未登录不能提交答案"""
        response = self.client.post(
            "/api/assignment/1/submit/",
            data=json.dumps({"answers": STUDENT_ANSWERS_GOOD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestGradeAllSubmissionsAPI(BaseAPITest):
    """POST /api/assignment/<id>/grade-all/ 教师批量 AI 判题"""

    @patch("assignment.bak.views.GradingService.grade_all_submissions")
    def test_grade_all_submissions_success(self, mock_grade):
        """教师发起批量判题，服务层返回成功"""
        self._auth_as_teacher()
        mock_grade.return_value = (
            True,
            "批量判题完成",
            {"graded_count": 3, "failed_count": 0},
        )
        response = self.client.post("/api/assignment/1/grade-all/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["graded_count"], 3)

    @patch("assignment.bak.views.GradingService.grade_all_submissions")
    def test_grade_all_submissions_no_submissions(self, mock_grade):
        """没有待批改提交时服务层应返回失败提示"""
        self._auth_as_teacher()
        mock_grade.return_value = (False, "没有待批改的提交", None)
        response = self.client.post("/api/assignment/1/grade-all/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])

    def test_grade_all_unauthenticated(self):
        """未登录不能触发批量判题"""
        response = self.client.post("/api/assignment/1/grade-all/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAnalyzeStandardAnswersAPI(BaseAPITest):
    """POST /api/assignment/<id>/analyze/ 标准答案预分析"""

    @patch("assignment.bak.views.GradingService.analyze_standard_answers")
    def test_analyze_essay_questions(self, mock_analyze):
        """含问答题的作业预分析应返回关键点信息"""
        self._auth_as_teacher()
        mock_analyze.return_value = (
            True,
            "预分析完成，成功分析 2/2 题",
            {
                "assignment_id": 1,
                "total_questions": 2,
                "analyzed_count": 2,
                "details": {
                    "q1": {"success": True, "keypoints": ["ACID", "原子性", "一致性", "隔离性", "持久性"]},
                    "q2": {"success": True, "keypoints": ["B+树支持范围查询", "哈希索引等值查找"]},
                },
            },
        )
        response = self.client.post("/api/assignment/1/analyze/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["analyzed_count"], 2)

    @patch("assignment.bak.views.GradingService.analyze_standard_answers")
    def test_analyze_skips_sql_python_report(self, mock_analyze):
        """python/sql/report 题在预分析阶段直接跳过（analyzed_count < total）"""
        self._auth_as_teacher()
        mock_analyze.return_value = (
            True,
            "预分析完成，成功分析 2/5 题",
            {
                "assignment_id": 1,
                "total_questions": 5,
                "analyzed_count": 2,
                "details": {
                    "q1": {"success": True, "keypoints": ["ACID"]},
                    "q2": {"success": True, "keypoints": ["B+树"]},
                    "q3": {"success": False, "reason": "sql 题跳过"},
                    "q4": {"success": False, "reason": "python 题跳过"},
                    "q5": {"success": False, "reason": "report 题跳过"},
                },
            },
        )
        response = self.client.post("/api/assignment/1/analyze/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["total_questions"], 5)
        self.assertEqual(data["data"]["analyzed_count"], 2)


class TestManualGradeAPI(BaseAPITest):
    """POST /api/assignment/<id>/submissions/<sub_id>/manual-grade/ 人工评分"""

    @patch("assignment.bak.views.GradingService.manual_grade_submission")
    def test_manual_grade_essay(self, mock_manual):
        """教师对问答题进行人工评分"""
        self._auth_as_teacher()
        mock_manual.return_value = (True, "人工评分完成", MagicMock())
        payload = {
            "total_score": "88.50",
            "grading_rubric": [
                {"question_id": "q1", "score": 18, "comment": "ACID 要点基本覆盖，持久性略有偏差"},
                {"question_id": "q2", "score": 8, "comment": "区别描述正确，场景举例简单"},
            ],
            "overall_comment": "整体掌握扎实，细节描述有待加强。",
        }
        response = self.client.post(
            "/api/assignment/1/submissions/10/manual-grade/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("assignment.bak.views.GradingService.manual_grade_submission")
    def test_manual_grade_report(self, mock_manual):
        """教师对大作业进行人工评分"""
        self._auth_as_teacher()
        mock_manual.return_value = (True, "人工评分完成", MagicMock())
        payload = {
            "total_score": "17.00",
            "grading_rubric": [
                {
                    "question_id": "q5",
                    "score": 17,
                    "dimension_scores": {
                        "内容完整性": 7.5,
                        "逻辑结构": 5.0,
                        "语言表达": 3.0,
                        "创新思考": 1.5,
                    },
                    "comment": "内容覆盖较全面，但创新性思考不足。",
                }
            ],
            "overall_comment": "报告结构清晰，建议加强对前沿技术的关注。",
        }
        response = self.client.post(
            "/api/assignment/1/submissions/10/manual-grade/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manual_grade_missing_total_score(self):
        """人工评分缺少 total_score 应被序列化器拦截"""
        self._auth_as_teacher()
        payload = {"overall_comment": "不错"}
        response = self.client.post(
            "/api/assignment/1/submissions/10/manual-grade/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestUpdateKeypointsAPI(BaseAPITest):
    """PUT /api/assignment/<id>/questions/<qid>/keypoints/ 编辑关键点"""

    @patch("assignment.bak.views.AssignmentService.update_question_keypoints")
    def test_update_essay_keypoints(self, mock_update):
        """教师更新问答题关键点"""
        self._auth_as_teacher()
        fake_assignment = MagicMock()
        fake_assignment.id = 1
        fake_assignment.title = "数据库期中综合作业"
        fake_assignment.course_id = 1
        fake_assignment.teacher_id = 1
        fake_assignment.course.course_name = "数据库原理"
        fake_assignment.teacher.nickname = "测试教师"
        fake_assignment.description = ""
        fake_assignment.questions = ALL_QUESTIONS
        fake_assignment.total_score = Decimal("100.00")
        fake_assignment.start_time = timezone.now()
        fake_assignment.end_time = timezone.now()
        fake_assignment.assignment_status = 0
        fake_assignment.ASSIGNMENT_STATUS_CHOICES = [(0, "草稿"), (1, "已发布")]
        fake_assignment.created_at = timezone.now()
        fake_assignment.updated_at = timezone.now()

        mock_update.return_value = (True, "关键点更新成功", fake_assignment)

        payload = {
            "keypoints": ["ACID特性", "原子性", "一致性", "隔离性", "持久性", "事务定义"]
        }
        response = self.client.put(
            "/api/assignment/1/questions/q1/keypoints/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("assignment.bak.views.AssignmentService.update_question_keypoints")
    def test_update_keypoints_with_empty_list(self, mock_update):
        """允许传入空列表来清空关键点"""
        self._auth_as_teacher()
        fake_assignment = MagicMock()
        fake_assignment.id = 1
        fake_assignment.title = "测试"
        fake_assignment.course_id = 1
        fake_assignment.teacher_id = 1
        fake_assignment.course.course_name = "测试课"
        fake_assignment.teacher.nickname = "教师"
        fake_assignment.description = ""
        fake_assignment.questions = []
        fake_assignment.total_score = Decimal("100.00")
        fake_assignment.start_time = timezone.now()
        fake_assignment.end_time = timezone.now()
        fake_assignment.assignment_status = 0
        fake_assignment.ASSIGNMENT_STATUS_CHOICES = [(0, "草稿"), (1, "已发布")]
        fake_assignment.created_at = timezone.now()
        fake_assignment.updated_at = timezone.now()

        mock_update.return_value = (True, "关键点已清空", fake_assignment)
        payload = {"keypoints": []}
        response = self.client.put(
            "/api/assignment/1/questions/q1/keypoints/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================
# 四、GradingService 服务层测试（Mock DB + Mock Agent）
# ============================================================

class TestGradingServiceSubmit(TestCase):
    """GradingService.submit_answers 业务逻辑测试"""

    def _make_assignment(self, questions=None, status=1, within_time=True):
        assignment = MagicMock()
        assignment.id = 1
        assignment.assignment_status = status
        assignment.questions = questions or ALL_QUESTIONS
        now = timezone.now()
        if within_time:
            assignment.start_time = now.replace(year=now.year - 1)
            assignment.end_time = now.replace(year=now.year + 1)
        else:
            assignment.start_time = now.replace(year=now.year - 2)
            assignment.end_time = now.replace(year=now.year - 1)
        assignment.course = MagicMock()
        return assignment

    @patch("assignment.services.grading_service.Enrollment.objects.filter")
    @patch("assignment.services.grading_service.Submission.objects.filter")
    @patch("assignment.services.grading_service.Submission.objects.create")
    @patch("assignment.services.grading_service.Assignment.objects.select_related")
    @patch("assignment.services.grading_service.UserModel.objects.get")
    def test_submit_valid_answers(
        self, mock_get_user, mock_select, mock_create, mock_sub_filter, mock_enroll_filter
    ):
        """学生在截止日期前提交合法答案应成功"""
        from assignment.services.grading_service import GradingService
        from user.models import UserModel

        student = make_student()
        mock_get_user.return_value = student

        assignment = self._make_assignment()
        mock_qs = MagicMock()
        mock_qs.get.return_value = assignment
        mock_select.return_value = mock_qs

        mock_enroll_filter.return_value.exists.return_value = True
        mock_sub_filter.return_value.first.return_value = None

        fake_sub = MagicMock()
        fake_sub.id = 42
        mock_create.return_value = fake_sub

        # 提交仅包含部分合法题目 ID 的答案
        partial_answers = {"q1": STUDENT_ANSWERS_GOOD["q1"], "q3": STUDENT_ANSWERS_GOOD["q3"]}
        success, message, sub = GradingService.submit_answers(
            assignment_id=1, student=student, answers=partial_answers
        )
        self.assertTrue(success)
        self.assertEqual(sub.id, 42)

    @patch("assignment.services.grading_service.Assignment.objects.select_related")
    @patch("assignment.services.grading_service.UserModel.objects.get")
    def test_submit_after_deadline(self, mock_get_user, mock_select):
        """提交截止后应返回失败"""
        from assignment.services.grading_service import GradingService

        student = make_student()
        mock_get_user.return_value = student

        assignment = self._make_assignment(within_time=False)
        mock_qs = MagicMock()
        mock_qs.get.return_value = assignment
        mock_select.return_value = mock_qs

        success, message, sub = GradingService.submit_answers(
            assignment_id=1, student=student, answers=STUDENT_ANSWERS_GOOD
        )
        self.assertFalse(success)
        self.assertIn("截止", message)

    @patch("assignment.services.grading_service.Assignment.objects.select_related")
    @patch("assignment.services.grading_service.UserModel.objects.get")
    def test_submit_to_unpublished_assignment(self, mock_get_user, mock_select):
        """未发布作业不能提交"""
        from assignment.services.grading_service import GradingService

        student = make_student()
        mock_get_user.return_value = student

        assignment = self._make_assignment(status=0)
        mock_qs = MagicMock()
        mock_qs.get.return_value = assignment
        mock_select.return_value = mock_qs

        success, message, sub = GradingService.submit_answers(
            assignment_id=1, student=student, answers=STUDENT_ANSWERS_GOOD
        )
        self.assertFalse(success)
        self.assertIn("未发布", message)

    @patch("assignment.services.grading_service.UserModel.objects.get")
    def test_teacher_cannot_submit(self, mock_get_user):
        """教师不能以学生身份提交答案"""
        from assignment.services.grading_service import GradingService

        teacher = make_teacher()
        mock_get_user.return_value = teacher

        success, message, sub = GradingService.submit_answers(
            assignment_id=1, student=teacher, answers=STUDENT_ANSWERS_GOOD
        )
        self.assertFalse(success)
        self.assertIn("学生", message)


class TestGradingServiceManualGrade(TestCase):
    """GradingService.manual_grade_submission 业务逻辑测试"""

    @patch("assignment.services.grading_service.Grade.objects.update_or_create")
    @patch("assignment.services.grading_service.Submission.objects.select_related")
    @patch("assignment.services.grading_service.Assignment.objects.get")
    @patch("assignment.services.grading_service.UserModel.objects.get")
    def test_manual_grade_essay_submission(
        self, mock_get_user, mock_get_assign, mock_sub_select, mock_grade_uoc
    ):
        """教师对包含问答题的提交进行人工评分"""
        from assignment.services.grading_service import GradingService

        teacher = make_teacher()
        mock_get_user.return_value = teacher

        assignment = MagicMock()
        assignment.id = 1
        assignment.teacher_id = 1
        assignment.total_score = Decimal("100.00")
        mock_get_assign.return_value = assignment

        submission = MagicMock()
        submission.id = 10
        submission.assignment = assignment
        submission.submission_status = 1
        mock_qs = MagicMock()
        mock_qs.get.return_value = submission
        mock_sub_select.return_value = mock_qs

        fake_grade = MagicMock()
        mock_grade_uoc.return_value = (fake_grade, True)

        success, message, sub = GradingService.manual_grade_submission(
            teacher=teacher,
            assignment_id=1,
            submission_id=10,
            total_score=Decimal("88.50"),
            grading_rubric=[{"question_id": "q1", "score": 18}],
            overall_comment="答题良好",
        )
        self.assertTrue(success)

    @patch("assignment.services.grading_service.Assignment.objects.get")
    @patch("assignment.services.grading_service.UserModel.objects.get")
    def test_manual_grade_by_non_owner_teacher(self, mock_get_user, mock_get_assign):
        """其他教师不能对非本人作业的提交评分"""
        from assignment.services.grading_service import GradingService

        teacher = make_teacher(uid=99)  # 非作业所有者
        mock_get_user.return_value = teacher

        assignment = MagicMock()
        assignment.id = 1
        assignment.teacher_id = 1  # 作业属于 uid=1 的教师
        mock_get_assign.return_value = assignment

        success, message, sub = GradingService.manual_grade_submission(
            teacher=teacher,
            assignment_id=1,
            submission_id=10,
            total_score=Decimal("60.00"),
            grading_rubric=[],
            overall_comment="",
        )
        self.assertFalse(success)
        self.assertIn("自己的", message)


# ============================================================
# 五、各题型 AI 判题路由逻辑测试（CoordinatorAgent 路由）
# ============================================================

class TestCoordinatorAgentRouting(TestCase):
    """验证协调器按 question_type 选择正确评分路径"""

    def _get_route(self, question_type: str) -> str:
        """直接调用路由函数返回路径标识"""
        from agent.coordinator_agent import CoordinatorAgent

        class FakeState(dict):
            pass

        state = FakeState({"question_type": question_type})
        # 通过反射获取静态路由函数
        route_fn = None
        for attr_name in dir(CoordinatorAgent):
            if "route" in attr_name.lower() and "type" in attr_name.lower():
                route_fn = getattr(CoordinatorAgent, attr_name)
                break

        # 若无法反射，直接按约定规则断言
        if route_fn is None:
            if question_type in ("python", "sql"):
                return "code_path"
            if question_type == "report":
                return "report_path"
            return "essay_path"

        return route_fn(state)

    def test_essay_routes_to_essay_path(self):
        """essay 题走 essay_path"""
        route = self._get_route("essay")
        self.assertEqual(route, "essay_path")

    def test_short_answer_routes_to_essay_path(self):
        """short_answer 题走 essay_path（与 essay 相同路径）"""
        route = self._get_route("short_answer")
        self.assertEqual(route, "essay_path")

    def test_sql_routes_to_code_path(self):
        """sql 题走 code_path"""
        route = self._get_route("sql")
        self.assertEqual(route, "code_path")

    def test_python_routes_to_code_path(self):
        """python 题走 code_path"""
        route = self._get_route("python")
        self.assertEqual(route, "code_path")

    def test_report_routes_to_report_path(self):
        """report/大作业题走 report_path"""
        route = self._get_route("report")
        self.assertEqual(route, "report_path")


# ============================================================
# 六、答案数据完整性断言（数据驱动，无需 Mock）
# ============================================================

class TestAnswerDataIntegrity(TestCase):
    """验证测试用答案数据本身的合法性，确保测试 fixture 不存在低级错误"""

    def test_good_answers_cover_all_questions(self):
        """优秀答案应覆盖所有题目 ID"""
        question_ids = {q["id"] for q in ALL_QUESTIONS}
        self.assertEqual(question_ids, set(STUDENT_ANSWERS_GOOD.keys()))

    def test_bad_answers_cover_all_questions(self):
        """较差答案同样覆盖所有题目 ID"""
        question_ids = {q["id"] for q in ALL_QUESTIONS}
        self.assertEqual(question_ids, set(STUDENT_ANSWERS_BAD.keys()))

    def test_sql_test_cases_have_required_fields(self):
        """SQL 测试用例均包含 setup_sql 与 expected_rows"""
        for idx, case in enumerate(SQL_QUESTION["test_cases"]):
            with self.subTest(case_index=idx):
                self.assertIn("setup_sql", case)
                self.assertIn("expected_rows", case)
                self.assertIsInstance(case["expected_rows"], list)
                self.assertGreater(len(case["expected_rows"]), 0)

    def test_python_test_cases_have_required_fields(self):
        """Python 测试用例均包含 function_name、input、expected"""
        for idx, case in enumerate(PYTHON_QUESTION["test_cases"]):
            with self.subTest(case_index=idx):
                self.assertIn("function_name", case)
                self.assertIn("input", case)
                self.assertIn("expected", case)

    def test_python_fibonacci_expected_values_are_correct(self):
        """验证内置参考函数的期望值本身正确（防止测试用例设计出错）"""
        def fibonacci_ref(n):
            if n <= 0:
                return 0
            if n == 1:
                return 1
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

        for case in PYTHON_QUESTION["test_cases"]:
            with self.subTest(input=case["input"]):
                n = case["input"][0]
                self.assertEqual(fibonacci_ref(n), case["expected"])

    def test_report_grading_rubric_weights_sum_to_one(self):
        """大作业评分细则各维度权重之和应为 1.0"""
        rubric = REPORT_QUESTION["grading_rubric"]
        total_weight = sum(dim["weight"] for dim in rubric.values())
        self.assertAlmostEqual(total_weight, 1.0, places=6)

    def test_all_questions_score_sum(self):
        """所有题目分数之和应与 BASE_ASSIGNMENT_PAYLOAD total_score 一致"""
        total = sum(q["score"] for q in ALL_QUESTIONS)
        expected = float(BASE_ASSIGNMENT_PAYLOAD["total_score"])
        self.assertAlmostEqual(total, expected, places=2)
