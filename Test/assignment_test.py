#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assignment 包集成测试
测试 AssignmentService（CRUD）+ GradingService（提交/查询/预分析/判题）

用法:
    python Test/assignment_test.py          # 默认 Mock 模式（不需要 LLM API）
    python Test/assignment_test.py --real   # Real 模式（需要 LLM API，完整端到端）
"""
import asyncio
import io
import json
import os
import sys
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lumina.settings')

import django
django.setup()

from django.utils import timezone
from dotenv import load_dotenv
load_dotenv()

from user.models import UserModel
from course.models import Course, Enrollment, Assignment, Submission, Grade
from assignment.services.assignment_service import AssignmentService
from assignment.services.grading_service import GradingService

# ============================================================
# 测试数据
# ============================================================

TAG = uuid.uuid4().hex[:8]

TEST_QUESTIONS = [
    {
        "id": 1,
        "content": "请解释什么是冒泡排序算法，并分析其时间复杂度。",
        "score": 6,
        "standard_answer": (
            "冒泡排序是一种简单的排序算法。它重复地遍历列表，比较相邻元素并在顺序错误时交换。"
            "每轮遍历后最大元素冒泡到末尾。"
            "最坏/平均时间复杂度 O(n²)，最好 O(n)，空间复杂度 O(1)。"
        ),
    },
    {
        "id": 2,
        "content": "简述快速排序的核心思想。",
        "score": 4,
        "standard_answer": (
            "快速排序基于分治思想：选一个基准元素，将数组分为两部分，"
            "左侧小于基准，右侧大于基准，然后对两部分递归排序。"
            "平均时间复杂度 O(n log n)。"
        ),
    },
]

STUDENT_ANSWERS = {
    "1": "冒泡排序就是两两比较，大的往后放，像气泡一样浮到最后。时间复杂度是O(n²)。",
    "2": "快速排序就是先找一个基准，然后把比它小的放左边，大的放右边，再分别排序。",
}

MOCK_KEYPOINTS_Q1 = [
    "冒泡排序通过比较相邻元素并交换来实现排序",
    "每轮遍历后最大元素冒泡到末尾",
    "最坏/平均时间复杂度 O(n²)",
    "最好时间复杂度 O(n)",
    "空间复杂度 O(1)",
]

MOCK_KEYPOINTS_Q2 = [
    "基于分治思想",
    "选择基准元素进行分区",
    "递归排序左右两部分",
    "平均时间复杂度 O(n log n)",
]


# ============================================================
# 工具函数
# ============================================================

class TestContext:
    """测试上下文，持有所有测试数据，用于清理"""
    def __init__(self):
        self.teacher = None
        self.student = None
        self.course = None
        self.enrollment = None
        self.assignment = None
        self.submission = None


def print_section(title: str):
    print(f"\n{'=' * 64}")
    print(f"  {title}")
    print(f"{'=' * 64}")


def print_sub(title: str):
    print(f"\n  --- {title} ---")


def print_ok(msg: str):
    print(f"    ✓ {msg}")


def print_fail(msg: str):
    print(f"    ✗ {msg}")


def print_info(msg: str):
    print(f"    · {msg}")


# ============================================================
# Setup / Cleanup
# ============================================================

def setup() -> TestContext:
    """在真实数据库中创建测试数据"""
    print_section("准备测试数据")
    ctx = TestContext()

    ctx.teacher = UserModel.objects.create(
        username=f"test_teacher_{TAG}",
        password="hashed_pw",
        nickname=f"测试教师_{TAG}",
        user_type=UserModel.TEACHER,
        status=UserModel.ENABLED,
        is_deleted=UserModel.NOT_DELETED,
    )
    print_ok(f"教师: ID={ctx.teacher.id}, username={ctx.teacher.username}")

    ctx.student = UserModel.objects.create(
        username=f"test_student_{TAG}",
        password="hashed_pw",
        nickname=f"测试学生_{TAG}",
        user_type=UserModel.STUDENT,
        status=UserModel.ENABLED,
        is_deleted=UserModel.NOT_DELETED,
    )
    print_ok(f"学生: ID={ctx.student.id}, username={ctx.student.username}")

    ctx.course = Course.objects.create(
        teacher=ctx.teacher,
        course_name=f"测试课程_{TAG}",
        course_description="用于 assignment 包测试",
        invite_code=f"INV{TAG}",
        status=1,
        is_deleted=False,
    )
    print_ok(f"课程: ID={ctx.course.id}, name={ctx.course.course_name}")

    ctx.enrollment = Enrollment.objects.create(
        course=ctx.course,
        student=ctx.student,
        enrollment_status=1,
        is_deleted=False,
    )
    print_ok(f"选课关系: 学生 {ctx.student.id} → 课程 {ctx.course.id}")

    return ctx


def cleanup(ctx: TestContext):
    """清理所有测试数据（倒序删除，避免外键冲突）"""
    print_section("清理测试数据")
    try:
        Grade.objects.filter(
            submission__assignment__course=ctx.course
        ).delete()
        print_ok("Grade 已清理")
    except Exception as e:
        print_fail(f"Grade 清理失败: {e}")

    try:
        Submission.objects.filter(
            assignment__course=ctx.course
        ).delete()
        print_ok("Submission 已清理")
    except Exception as e:
        print_fail(f"Submission 清理失败: {e}")

    try:
        Assignment.objects.filter(course=ctx.course).delete()
        print_ok("Assignment 已清理")
    except Exception as e:
        print_fail(f"Assignment 清理失败: {e}")

    try:
        Enrollment.objects.filter(course=ctx.course).delete()
        print_ok("Enrollment 已清理")
    except Exception as e:
        print_fail(f"Enrollment 清理失败: {e}")

    try:
        ctx.course.delete()
        print_ok("Course 已清理")
    except Exception as e:
        print_fail(f"Course 清理失败: {e}")

    for user in [ctx.teacher, ctx.student]:
        try:
            if user:
                user.delete()
                print_ok(f"User {user.username} 已清理")
        except Exception as e:
            print_fail(f"User 清理失败: {e}")


# ============================================================
# 测试 1: AssignmentService CRUD
# ============================================================

def test_assignment_crud(ctx: TestContext) -> bool:
    print_section("测试 1: AssignmentService CRUD")
    passed = True

    # 1.1 创建作业
    print_sub("1.1 创建作业")
    now = timezone.now()
    create_data = {
        "course_id": ctx.course.id,
        "title": f"测试作业_{TAG}",
        "description": "算法基础测试",
        "questions": TEST_QUESTIONS,
        "total_score": 10,
        "start_time": now - timedelta(hours=1),
        "end_time": now + timedelta(days=7),
    }
    ok, msg, assignment = AssignmentService.create_assignment(
        teacher=ctx.teacher, data=create_data,
    )
    if ok and assignment:
        ctx.assignment = assignment
        print_ok(f"创建成功: ID={assignment.id}, 状态={assignment.assignment_status}")
        print_info(f"题目数={len(assignment.questions)}, 总分={assignment.total_score}")
    else:
        print_fail(f"创建失败: {msg}")
        return False

    # 1.2 权限校验：学生不能创建作业
    print_sub("1.2 权限校验 - 学生创建作业")
    ok2, msg2, _ = AssignmentService.create_assignment(
        teacher=ctx.student, data=create_data,
    )
    if not ok2:
        print_ok(f"正确拒绝: {msg2}")
    else:
        print_fail("学生不应能创建作业")
        passed = False

    # 1.3 作业列表
    print_sub("1.3 作业列表")
    ok3, _, teacher_list = AssignmentService.list_assignments(
        course_id=ctx.course.id, user=ctx.teacher,
    )
    ok4, _, student_list = AssignmentService.list_assignments(
        course_id=ctx.course.id, user=ctx.student,
    )
    teacher_sees = any(a.id == assignment.id for a in teacher_list) if ok3 else False
    student_sees = any(a.id == assignment.id for a in student_list) if ok4 else False

    if teacher_sees:
        print_ok(f"教师可见草稿作业 (列表长度={len(teacher_list)})")
    else:
        print_fail("教师应能看到草稿作业")
        passed = False

    if not student_sees:
        print_ok("学生看不到草稿作业 (符合预期)")
    else:
        print_fail("学生不应看到草稿作业")
        passed = False

    # 1.4 获取详情
    print_sub("1.4 获取作业详情")
    ok5, _, detail = AssignmentService.get_assignment_detail(assignment.id)
    if ok5 and detail:
        print_ok(f"获取成功: title={detail.title}, questions={len(detail.questions)}")
    else:
        print_fail("获取详情失败")
        passed = False

    # 1.5 更新作业
    print_sub("1.5 更新作业（草稿状态）")
    ok6, msg6, updated = AssignmentService.update_assignment(
        teacher=ctx.teacher,
        assignment_id=assignment.id,
        data={"title": f"测试作业_修改_{TAG}", "description": "更新后的描述"},
    )
    if ok6 and updated:
        print_ok(f"更新成功: title={updated.title}")
    else:
        print_fail(f"更新失败: {msg6}")
        passed = False

    # 1.6 发布作业
    print_sub("1.6 发布作业")
    ok7, msg7 = AssignmentService.publish_assignment(
        teacher=ctx.teacher, assignment_id=assignment.id,
    )
    if ok7:
        assignment.refresh_from_db()
        print_ok(f"发布成功: status={assignment.assignment_status}")
    else:
        print_fail(f"发布失败: {msg7}")
        passed = False

    # 1.7 发布后不能修改
    print_sub("1.7 发布后尝试修改")
    ok8, msg8, _ = AssignmentService.update_assignment(
        teacher=ctx.teacher,
        assignment_id=assignment.id,
        data={"title": "不该成功"},
    )
    if not ok8:
        print_ok(f"正确拒绝: {msg8}")
    else:
        print_fail("发布后不应能修改")
        passed = False

    # 1.8 学生现在可以看到已发布作业
    print_sub("1.8 学生查看已发布作业")
    ok9, _, student_list2 = AssignmentService.list_assignments(
        course_id=ctx.course.id, user=ctx.student,
    )
    student_sees2 = any(a.id == assignment.id for a in student_list2) if ok9 else False
    if student_sees2:
        print_ok("学生可以看到已发布作业")
    else:
        print_fail("学生应能看到已发布作业")
        passed = False

    return passed


# ============================================================
# 测试 2: GradingService 提交与查询
# ============================================================

def test_submission_and_query(ctx: TestContext) -> bool:
    print_section("测试 2: GradingService 提交与查询")
    passed = True

    if not ctx.assignment:
        print_fail("缺少作业数据，跳过")
        return False

    # 2.1 学生提交答案
    print_sub("2.1 学生提交答案")
    ok, msg, submission = GradingService.submit_answers(
        assignment_id=ctx.assignment.id,
        student=ctx.student,
        answers=STUDENT_ANSWERS,
    )
    if ok and submission:
        ctx.submission = submission
        print_ok(f"提交成功: ID={submission.id}, status={submission.submission_status}")
        print_info(f"answers keys: {list(submission.answers.keys())}")
    else:
        print_fail(f"提交失败: {msg}")
        return False

    # 2.2 教师不能提交答案
    print_sub("2.2 权限校验 - 教师提交答案")
    ok2, msg2, _ = GradingService.submit_answers(
        assignment_id=ctx.assignment.id,
        student=ctx.teacher,
        answers=STUDENT_ANSWERS,
    )
    if not ok2:
        print_ok(f"正确拒绝: {msg2}")
    else:
        print_fail("教师不应能提交答案")
        passed = False

    # 2.3 无效题目 ID
    print_sub("2.3 无效题目 ID")
    ok3, msg3, _ = GradingService.submit_answers(
        assignment_id=ctx.assignment.id,
        student=ctx.student,
        answers={"999": "不存在的题目"},
    )
    if not ok3:
        print_ok(f"正确拒绝: {msg3}")
    else:
        print_fail("应拒绝无效题目 ID")
        passed = False

    # 2.4 重复提交（覆盖）
    print_sub("2.4 重复提交（覆盖已有）")
    updated_answers = {"1": "修改后的答案", "2": "修改后的答案2"}
    ok4, msg4, re_submission = GradingService.submit_answers(
        assignment_id=ctx.assignment.id,
        student=ctx.student,
        answers=updated_answers,
    )
    if ok4 and re_submission:
        print_ok(f"覆盖成功: ID={re_submission.id} (应与首次相同)")
        print_info(f"answers[1]={re_submission.answers.get('1', '')[:30]}")
        ctx.submission = re_submission
    else:
        print_fail(f"覆盖失败: {msg4}")
        passed = False

    # 恢复原始答案供后续判题测试使用
    GradingService.submit_answers(
        assignment_id=ctx.assignment.id,
        student=ctx.student,
        answers=STUDENT_ANSWERS,
    )

    # 2.5 教师查看所有提交
    print_sub("2.5 教师查看所有提交")
    ok5, _, submissions = GradingService.get_submissions(
        assignment_id=ctx.assignment.id,
        teacher=ctx.teacher,
    )
    if ok5 and len(submissions) > 0:
        print_ok(f"获取成功: {len(submissions)} 条提交")
        for s in submissions:
            print_info(f"  ID={s.id}, 学生={s.student.nickname}, status={s.submission_status}")
    else:
        print_fail("获取提交列表失败")
        passed = False

    # 2.6 学生查看自己的提交
    print_sub("2.6 学生查看自己的提交")
    ok6, _, my_sub = GradingService.get_my_submission(
        assignment_id=ctx.assignment.id,
        student=ctx.student,
    )
    if ok6 and my_sub:
        print_ok(f"获取成功: ID={my_sub.id}, status={my_sub.submission_status}")
    else:
        print_fail("学生获取自己的提交失败")
        passed = False

    return passed


# ============================================================
# 测试 3: GradingService 预分析标准答案（Mock 模式）
# ============================================================

def test_analyze_mock(ctx: TestContext) -> bool:
    print_section("测试 3: 预分析标准答案 (Mock 模式)")
    passed = True

    if not ctx.assignment:
        print_fail("缺少作业数据，跳过")
        return False

    async def fake_analyze_all_questions(questions):
        """模拟分析结果"""
        results = {}
        mock_data = {"1": MOCK_KEYPOINTS_Q1, "2": MOCK_KEYPOINTS_Q2}
        for q in questions:
            q_id = str(q.get("id"))
            results[q_id] = {
                "success": True,
                "keypoints": mock_data.get(q_id, ["模拟关键点"]),
                "keypoint_count": len(mock_data.get(q_id, [])),
                "summary": "模拟摘要",
                "quality_score": 0.9,
                "difficulty_estimate": "medium",
            }
        return results

    print_sub("3.1 教师预分析标准答案")
    with patch.object(
        GradingService, '_analyze_all_questions', side_effect=fake_analyze_all_questions
    ):
        ok, msg, data = GradingService.analyze_standard_answers(
            assignment_id=ctx.assignment.id,
            teacher=ctx.teacher,
        )

    if ok and data:
        print_ok(f"分析完成: {msg}")
        print_info(f"total={data['total_questions']}, analyzed={data['analyzed_count']}")

        ctx.assignment.refresh_from_db()
        for q in ctx.assignment.questions:
            kps = q.get('answer_keypoints', [])
            analyzed = q.get('analyzed', False)
            print_info(f"  题目 {q['id']}: analyzed={analyzed}, keypoints={len(kps)}")
            if not analyzed or len(kps) == 0:
                print_fail(f"题目 {q['id']} 未正确写入关键点")
                passed = False
    else:
        print_fail(f"预分析失败: {msg}")
        passed = False

    # 3.2 权限校验
    print_sub("3.2 权限校验 - 学生预分析")
    ok2, msg2, _ = GradingService.analyze_standard_answers(
        assignment_id=ctx.assignment.id,
        teacher=ctx.student,
    )
    if not ok2:
        print_ok(f"正确拒绝: {msg2}")
    else:
        print_fail("学生不应能预分析")
        passed = False

    return passed


# ============================================================
# 测试 4: GradingService 批量判题（Mock 模式）
# ============================================================

def test_grade_mock(ctx: TestContext) -> bool:
    print_section("测试 4: 批量判题 (Mock 模式)")
    passed = True

    if not ctx.assignment or not ctx.submission:
        print_fail("缺少作业/提交数据，跳过")
        return False

    async def fake_grade_submissions(submissions):
        """模拟判题结果，ORM 操作需要通过 sync_to_async 包装"""
        from asgiref.sync import sync_to_async

        def _persist(sub):
            sub.submission_status = 2
            sub.total_score = 7.5
            sub.graded_at = timezone.now()
            sub.save(update_fields=[
                'submission_status', 'total_score', 'graded_at', 'updated_at'
            ])
            Grade.objects.update_or_create(
                submission=sub,
                defaults={
                    "grading_rubric": [
                        {"question_id": 1, "score": 4.5, "max_score": 6, "status": "completed"},
                        {"question_id": 2, "score": 3.0, "max_score": 4, "status": "completed"},
                    ],
                    "overall_comment": "模拟评语",
                    "is_deleted": False,
                },
            )

        results = []
        for sub in submissions:
            await sync_to_async(_persist)(sub)
            results.append({
                "submission_id": sub.id,
                "student_id": sub.student_id,
                "status": "completed",
                "total_score": 7.5,
                "overall_comment": "模拟评语：共2题，总分7.5/10",
            })
        return results

    print_sub("4.1 教师批量判题")
    with patch.object(
        GradingService, '_grade_submissions_async', side_effect=fake_grade_submissions
    ):
        ok, msg, data = GradingService.grade_all_submissions(
            assignment_id=ctx.assignment.id,
            teacher=ctx.teacher,
        )

    if ok and data:
        print_ok(f"判题完成: {msg}")
        print_info(
            f"total={data['total']}, "
            f"success={data['success_count']}, error={data['error_count']}"
        )
        for r in data.get('results', []):
            print_info(
                f"  提交ID={r['submission_id']}, "
                f"score={r.get('total_score')}, status={r['status']}"
            )
    else:
        print_fail(f"批量判题失败: {msg}")
        passed = False

    # 4.2 验证 Submission 状态已更新
    print_sub("4.2 验证数据库更新")
    ctx.submission.refresh_from_db()
    if ctx.submission.submission_status == 2:
        print_ok(f"Submission 状态已更新: status={ctx.submission.submission_status}")
        print_info(f"total_score={ctx.submission.total_score}, graded_at={ctx.submission.graded_at}")
    else:
        print_fail(f"Submission 状态未更新: status={ctx.submission.submission_status}")
        passed = False

    # 4.3 验证 Grade 已生成
    try:
        grade = Grade.objects.get(submission=ctx.submission)
        print_ok(f"Grade 已生成: rubric 条数={len(grade.grading_rubric)}")
        print_info(f"overall_comment={grade.overall_comment[:50]}")
    except Grade.DoesNotExist:
        print_fail("Grade 未生成")
        passed = False

    # 4.4 学生查看成绩
    print_sub("4.4 学生查看成绩")
    ok4, _, my_sub = GradingService.get_my_submission(
        assignment_id=ctx.assignment.id,
        student=ctx.student,
    )
    if ok4 and my_sub:
        print_ok(f"获取成功: score={my_sub.total_score}, status={my_sub.submission_status}")
        try:
            g = my_sub.grade
            print_info(f"评分细则条数={len(g.grading_rubric)}")
        except Grade.DoesNotExist:
            print_info("无成绩详情（尚未生成）")
    else:
        print_fail("学生查看成绩失败")
        passed = False

    # 4.5 已批改不能再提交
    print_sub("4.5 已批改后再次提交")
    ok5, msg5, _ = GradingService.submit_answers(
        assignment_id=ctx.assignment.id,
        student=ctx.student,
        answers=STUDENT_ANSWERS,
    )
    if not ok5:
        print_ok(f"正确拒绝: {msg5}")
    else:
        print_fail("已批改后不应能再次提交")
        passed = False

    return passed


# ============================================================
# 测试 5 (可选): Real 模式 - 完整端到端
# ============================================================

def test_analyze_real(ctx: TestContext) -> bool:
    """调用真实 LLM 进行标准答案预分析"""
    print_section("测试 5: 预分析标准答案 (Real 模式 - LLM)")

    # 先重置 analyzed 状态
    for q in ctx.assignment.questions:
        q['answer_keypoints'] = []
        q['analyzed'] = False
    ctx.assignment.save(update_fields=['questions', 'updated_at'])

    ok, msg, data = GradingService.analyze_standard_answers(
        assignment_id=ctx.assignment.id,
        teacher=ctx.teacher,
    )

    if ok and data:
        print_ok(f"分析完成: {msg}")
        ctx.assignment.refresh_from_db()
        for q in ctx.assignment.questions:
            kps = q.get('answer_keypoints', [])
            print_info(f"  题目 {q['id']}: keypoints={len(kps)} 个")
            for kp in kps[:3]:
                print_info(f"    - {kp}")
            if len(kps) > 3:
                print_info(f"    ... 共 {len(kps)} 个")
        return True
    else:
        print_fail(f"分析失败: {msg}")
        return False


def test_grade_real(ctx: TestContext) -> bool:
    """调用真实 LLM 进行判题（需要先重置提交状态）"""
    print_section("测试 6: 批量判题 (Real 模式 - LLM)")

    ctx.submission.submission_status = 1
    ctx.submission.total_score = 0
    ctx.submission.graded_at = None
    ctx.submission.save(update_fields=[
        'submission_status', 'total_score', 'graded_at', 'updated_at'
    ])
    Grade.objects.filter(submission=ctx.submission).delete()

    ok, msg, data = GradingService.grade_all_submissions(
        assignment_id=ctx.assignment.id,
        teacher=ctx.teacher,
    )

    if ok and data:
        print_ok(f"判题完成: {msg}")
        for r in data.get('results', []):
            print_info(
                f"  提交ID={r['submission_id']}, "
                f"score={r.get('total_score')}, status={r['status']}"
            )
        ctx.submission.refresh_from_db()
        print_info(f"  最终得分: {ctx.submission.total_score}/{ctx.assignment.total_score}")
        return True
    else:
        print_fail(f"判题失败: {msg}")
        return False


# ============================================================
# 主入口
# ============================================================

def main():
    real_mode = "--real" in sys.argv

    print_section(f"Assignment 包集成测试 ({'Real 模式' if real_mode else 'Mock 模式'})")

    ctx = None
    results = {}

    try:
        ctx = setup()

        results["1. AssignmentService CRUD"] = test_assignment_crud(ctx)
        results["2. 提交与查询"] = test_submission_and_query(ctx)
        results["3. 预分析标准答案 (Mock)"] = test_analyze_mock(ctx)
        results["4. 批量判题 (Mock)"] = test_grade_mock(ctx)

        if real_mode:
            # 重置状态给 real 测试
            for q in ctx.assignment.questions:
                q['answer_keypoints'] = []
                q['analyzed'] = False
            ctx.assignment.save(update_fields=['questions'])

            ctx.submission.submission_status = 1
            ctx.submission.total_score = 0
            ctx.submission.graded_at = None
            ctx.submission.save(update_fields=[
                'submission_status', 'total_score', 'graded_at'
            ])
            Grade.objects.filter(submission=ctx.submission).delete()

            results["5. 预分析 (Real LLM)"] = test_analyze_real(ctx)
            results["6. 批量判题 (Real LLM)"] = test_grade_real(ctx)

    except Exception as e:
        print(f"\n  !! 测试过程出现异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ctx:
            cleanup(ctx)

    # 汇总
    print_section("测试汇总")
    for name, passed in results.items():
        icon = "✓" if passed else "✗"
        print(f"  {icon} {name}")

    total = len(results)
    passed_count = sum(1 for v in results.values() if v)
    print(f"\n  通过 {passed_count}/{total}")

    if passed_count == total:
        print("\n  全部通过！Assignment 包开发验证完成。")
    else:
        print("\n  存在失败项，请查看上方详细输出。")

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
