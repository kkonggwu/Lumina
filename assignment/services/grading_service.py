#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
判题服务层
处理学生提交、标准答案预分析、批量判题、成绩查询等业务逻辑
"""
from typing import Tuple, Optional, List

from asgiref.sync import async_to_sync
from django.utils import timezone

from course.models import Assignment, Submission, Grade, Enrollment
from user.models import UserModel
from utils.logger import get_logger

logger = get_logger('grading_service')


class GradingService:
    """判题服务类"""

    # ==================== 学生提交 ====================

    @staticmethod
    def submit_answers(
        assignment_id: int, student, answers: dict
    ) -> Tuple[bool, str, Optional[Submission]]:
        """
        学生提交答案
        :param assignment_id: 作业 ID
        :param student: 当前登录用户（学生）
        :param answers: 答案字典 {question_id_str: answer_text}
        :return: (success, message, submission)
        """
        try:
            # 兼容 JWT TokenUser，通过 id 获取真实用户
            if not isinstance(student, UserModel):
                try:
                    student = UserModel.objects.get(id=getattr(student, "id", None), is_deleted=UserModel.NOT_DELETED)
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", None

            if student.user_type != UserModel.STUDENT:
                return False, "仅学生可以提交答案", None

            try:
                assignment = Assignment.objects.select_related('course').get(
                    id=assignment_id, is_deleted=False
                )
            except Assignment.DoesNotExist:
                return False, "作业不存在", None

            if assignment.assignment_status != 1:
                return False, "作业未发布，无法提交", None

            now = timezone.now()
            if now < assignment.start_time:
                return False, "作业未开始", None
            if now > assignment.end_time:
                return False, "作业已截止", None

            enrolled = Enrollment.objects.filter(
                course=assignment.course,
                student=student,
                enrollment_status=1,
                is_deleted=False,
            ).exists()
            if not enrolled:
                return False, "未加入该课程，无法提交", None

            # 校验答案中的题目 ID 是否都属于该作业
            question_ids = {str(q.get('id')) for q in (assignment.questions or [])}
            invalid_ids = set(answers.keys()) - question_ids
            if invalid_ids:
                return False, f"答案中包含无效的题目 ID: {', '.join(invalid_ids)}", None

            existing = Submission.objects.filter(
                assignment=assignment, student=student, is_deleted=False
            ).first()

            if existing and existing.submission_status == 2:
                return False, "该作业已批改，不能重复提交", None

            if existing:
                existing.answers = answers
                existing.submission_status = 1
                existing.submitted_at = timezone.now()
                existing.save(update_fields=[
                    'answers', 'submission_status', 'submitted_at', 'updated_at'
                ])
                submission = existing
                logger.info(f"学生重新提交: 提交ID={submission.id}")
            else:
                submission = Submission.objects.create(
                    assignment=assignment,
                    student=student,
                    answers=answers,
                    submission_status=1,
                    submitted_at=timezone.now(),
                )
                logger.info(f"学生提交成功: 提交ID={submission.id}")

            return True, "提交成功", submission

        except Exception as e:
            logger.error(f"提交答案失败: {str(e)}", exc_info=True)
            return False, f"提交失败: {str(e)}", None

    # ==================== 标准答案预分析 ====================

    @staticmethod
    def analyze_standard_answers(
        assignment_id: int, teacher
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        预分析标准答案（教师操作）
        使用 AnalyzerAgent 提取每道题标准答案的关键要点，并缓存到 assignment.questions 中
        :param assignment_id: 作业 ID
        :param teacher: 当前登录用户（教师）
        :return: (success, message, data)
        """
        try:
            from user.models import UserModel  # 避免循环依赖放在内部
            # 兼容 JWT TokenUser，通过 id 获取真实用户
            if not isinstance(teacher, UserModel):
                try:
                    teacher = UserModel.objects.get(id=getattr(teacher, "id", None), is_deleted=UserModel.NOT_DELETED)
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", None

            if teacher.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
                return False, "仅教师和管理员可执行此操作", None

            try:
                assignment = Assignment.objects.get(
                    id=assignment_id, is_deleted=False
                )
            except Assignment.DoesNotExist:
                return False, "作业不存在", None

            if teacher.user_type == UserModel.TEACHER and assignment.teacher_id != teacher.id:
                return False, "只能操作自己的作业", None

            questions = assignment.questions or []
            if not questions:
                return False, "作业没有题目", None

            analysis_results = async_to_sync(
                GradingService._analyze_all_questions
            )(questions)

            updated_count = 0
            for q in questions:
                q_id = str(q.get('id'))
                result = analysis_results.get(q_id, {})
                if result.get('success'):
                    q['answer_keypoints'] = result['keypoints']
                    q['analyzed'] = True
                    updated_count += 1

            assignment.questions = questions
            assignment.save(update_fields=['questions', 'updated_at'])

            logger.info(
                f"标准答案预分析完成: 作业ID={assignment_id}, "
                f"更新 {updated_count}/{len(questions)} 题"
            )

            return True, f"预分析完成，成功分析 {updated_count}/{len(questions)} 题", {
                "assignment_id": assignment_id,
                "total_questions": len(questions),
                "analyzed_count": updated_count,
                "details": analysis_results,
            }

        except Exception as e:
            logger.error(f"预分析标准答案失败: {str(e)}", exc_info=True)
            return False, f"预分析失败: {str(e)}", None

    # 不需要关键点预分析的题目类型（由专用 Agent 直接评分）
    _NON_KEYPOINT_TYPES = {"python", "sql", "report"}

    @staticmethod
    async def _analyze_all_questions(questions: list) -> dict:
        """
        异步分析所有题目的标准答案关键点。
        python / sql / report 类型由专用 Agent 处理，跳过此预分析阶段。
        """
        from agent.analyzer_agent import AnalyzerAgent

        analyzer = AnalyzerAgent()
        results = {}

        for q in questions:
            q_id = str(q.get('id'))
            content = q.get('content', '')
            standard_answer = q.get('standard_answer', '')
            q_type = q.get('question_type', 'essay')

            # 代码题和报告题不走关键点流程，跳过预分析
            if q_type in GradingService._NON_KEYPOINT_TYPES:
                logger.info(f"题目 {q_id} 类型={q_type}，跳过关键点预分析")
                results[q_id] = {
                    'success': True,
                    'skipped': True,
                    'reason': f'{q_type} 类型题目由专用 Agent 评分，无需关键点预分析',
                    'keypoints': [],
                }
                continue

            if not standard_answer:
                results[q_id] = {
                    'success': False,
                    'error': '缺少标准答案',
                    'keypoints': [],
                }
                continue

            try:
                result = await analyzer.analyze_standard_answer(
                    question=content,
                    standard_answer=standard_answer,
                )
                results[q_id] = result
                logger.info(
                    f"题目 {q_id} 分析完成: "
                    f"关键点 {len(result.get('keypoints', []))} 个"
                )
            except Exception as e:
                logger.error(f"题目 {q_id} 分析异常: {str(e)}")
                results[q_id] = {
                    'success': False,
                    'error': str(e),
                    'keypoints': [],
                }

        return results

    # ==================== 批量判题 ====================

    @staticmethod
    def grade_all_submissions(
        assignment_id: int, teacher
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        批量判题（教师操作）
        对指定作业下所有已提交待批改的答案进行 AI 判题
        :param assignment_id: 作业 ID
        :param teacher: 当前登录用户（教师）
        :return: (success, message, data)
        """
        try:
            from user.models import UserModel  # 避免循环依赖放在内部
            if not isinstance(teacher, UserModel):
                try:
                    teacher = UserModel.objects.get(id=getattr(teacher, "id", None), is_deleted=UserModel.NOT_DELETED)
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", None

            if teacher.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
                return False, "仅教师和管理员可执行此操作", None

            try:
                assignment = Assignment.objects.get(
                    id=assignment_id, is_deleted=False
                )
            except Assignment.DoesNotExist:
                return False, "作业不存在", None

            if teacher.user_type == UserModel.TEACHER and assignment.teacher_id != teacher.id:
                return False, "只能操作自己的作业", None

            submissions = list(
                Submission.objects.filter(
                    assignment=assignment,
                    submission_status=1,
                    is_deleted=False,
                )
            )

            if not submissions:
                return False, "没有待批改的提交", None

            grade_results = async_to_sync(
                GradingService._grade_submissions_async
            )(submissions)

            success_count = sum(
                1 for r in grade_results if r.get('status') in ('completed', 'partial')
            )
            error_count = sum(
                1 for r in grade_results if r.get('status') == 'error'
            )

            logger.info(
                f"批量判题完成: 作业ID={assignment_id}, "
                f"总数={len(submissions)}, 成功={success_count}, 失败={error_count}"
            )

            return True, f"判题完成，成功 {success_count}/{len(submissions)}", {
                "assignment_id": assignment_id,
                "total": len(submissions),
                "success_count": success_count,
                "error_count": error_count,
                "results": grade_results,
            }

        except Exception as e:
            logger.error(f"批量判题失败: {str(e)}", exc_info=True)
            return False, f"批量判题失败: {str(e)}", None

    @staticmethod
    async def _grade_submissions_async(submissions: list) -> list:
        """异步判题所有提交"""
        from agent.coordinator_agent import CoordinatorAgent

        coordinator = CoordinatorAgent()
        results = []

        for submission in submissions:
            try:
                result = await coordinator.grade_submission(submission.id)
                results.append({
                    "submission_id": submission.id,
                    "student_id": submission.student_id,
                    "status": result.get("status", "error"),
                    "total_score": result.get("total_score", 0),
                    "overall_comment": result.get("overall_comment", ""),
                })
            except Exception as e:
                logger.error(
                    f"判题失败: 提交ID={submission.id}, 错误={str(e)}"
                )
                results.append({
                    "submission_id": submission.id,
                    "student_id": submission.student_id,
                    "status": "error",
                    "error_message": str(e),
                })

        return results

    # ==================== 查询 ====================

    @staticmethod
    def get_submissions(
        assignment_id: int, teacher
    ) -> Tuple[bool, str, List[Submission]]:
        """
        获取作业的所有提交（教师查看）
        :param assignment_id: 作业 ID
        :param teacher: 当前登录用户（教师）
        :return: (success, message, submissions)
        """
        try:
            from user.models import UserModel  # 避免循环依赖放在内部
            if not isinstance(teacher, UserModel):
                try:
                    teacher = UserModel.objects.get(id=getattr(teacher, "id", None), is_deleted=UserModel.NOT_DELETED)
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", []

            if teacher.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
                return False, "仅教师和管理员可查看所有提交", []

            try:
                assignment = Assignment.objects.get(
                    id=assignment_id, is_deleted=False
                )
            except Assignment.DoesNotExist:
                return False, "作业不存在", []

            if teacher.user_type == UserModel.TEACHER and assignment.teacher_id != teacher.id:
                return False, "只能查看自己作业的提交", []

            submissions = list(
                Submission.objects.select_related('student').filter(
                    assignment=assignment,
                    is_deleted=False,
                    submission_status__gte=1,
                ).order_by('-submitted_at')
            )

            return True, "获取成功", submissions

        except Exception as e:
            logger.error(f"获取提交列表失败: {str(e)}", exc_info=True)
            return False, f"获取失败: {str(e)}", []

    @staticmethod
    def get_my_submission(
        assignment_id: int, student
    ) -> Tuple[bool, str, Optional[Submission]]:
        """
        获取学生自己的提交和成绩
        :param assignment_id: 作业 ID
        :param student: 当前登录用户（学生）
        :return: (success, message, submission)
        """
        try:
            # 兼容 JWT TokenUser，通过 id 获取真实用户
            if not isinstance(student, UserModel):
                try:
                    student = UserModel.objects.get(id=getattr(student, "id", None), is_deleted=UserModel.NOT_DELETED)
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", None

            try:
                assignment = Assignment.objects.get(
                    id=assignment_id, is_deleted=False
                )
            except Assignment.DoesNotExist:
                return False, "作业不存在", None

            try:
                submission = Submission.objects.select_related(
                    'student'
                ).get(
                    assignment=assignment,
                    student=student,
                    is_deleted=False,
                )
                return True, "获取成功", submission
            except Submission.DoesNotExist:
                return False, "尚未提交", None

        except Exception as e:
            logger.error(f"获取提交详情失败: {str(e)}", exc_info=True)
            return False, f"获取失败: {str(e)}", None

    # ==================== 教师人工判题 ====================

    @staticmethod
    def get_submission_detail_for_teacher(
        assignment_id: int, submission_id: int, teacher
    ) -> Tuple[bool, str, Optional[Submission]]:
        """
        教师查看指定提交详情（用于评分报告界面）
        """
        try:
            from user.models import UserModel  # 避免循环依赖放在内部

            if not isinstance(teacher, UserModel):
                try:
                    teacher = UserModel.objects.get(
                        id=getattr(teacher, "id", None),
                        is_deleted=UserModel.NOT_DELETED,
                    )
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", None

            if teacher.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
                return False, "仅教师和管理员可查看提交详情", None

            try:
                assignment = Assignment.objects.get(
                    id=assignment_id, is_deleted=False
                )
            except Assignment.DoesNotExist:
                return False, "作业不存在", None

            if teacher.user_type == UserModel.TEACHER and assignment.teacher_id != teacher.id:
                return False, "只能查看自己作业的提交", None

            try:
                submission = Submission.objects.select_related("student").get(
                    id=submission_id,
                    assignment=assignment,
                    is_deleted=False,
                )
                return True, "获取成功", submission
            except Submission.DoesNotExist:
                return False, "提交记录不存在", None

        except Exception as e:
            logger.error(f"获取提交详情失败: {str(e)}", exc_info=True)
            return False, f"获取失败: {str(e)}", None

    @staticmethod
    def manual_grade_submission(
        submission_id: int,
        teacher,
        total_score,
        grading_rubric=None,
        overall_comment: str = "",
    ) -> Tuple[bool, str, Optional[Grade]]:
        """
        教师对单个提交进行人工评分 / 修订评分。

        逻辑：
        1. 校验教师身份和作业归属
        2. 更新 Submission.total_score / submission_status / graded_at
        3. 创建或更新 Grade 记录（grading_rubric + overall_comment）
        """
        try:
            from user.models import UserModel  # 避免循环依赖

            # 兼容 TokenUser
            if not isinstance(teacher, UserModel):
                try:
                    teacher = UserModel.objects.get(
                        id=getattr(teacher, "id", None),
                        is_deleted=UserModel.NOT_DELETED,
                    )
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", None

            if teacher.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
                return False, "仅教师和管理员可执行此操作", None

            try:
                submission = Submission.objects.select_related("assignment").get(
                    id=submission_id,
                    is_deleted=False,
                )
            except Submission.DoesNotExist:
                return False, "提交记录不存在", None

            assignment = submission.assignment
            if teacher.user_type == UserModel.TEACHER and assignment.teacher_id != teacher.id:
                return False, "只能批改自己课程下的作业", None

            # 更新 Submission 主记录
            submission.total_score = total_score
            submission.submission_status = 2  # 已批改
            submission.graded_at = timezone.now()
            submission.save(
                update_fields=["total_score", "submission_status", "graded_at", "updated_at"]
            )

            # 创建或更新 Grade 详情
            grading_rubric = grading_rubric if grading_rubric is not None else []
            grade, _ = Grade.objects.update_or_create(
                submission=submission,
                defaults={
                    "grading_rubric": grading_rubric,
                    "overall_comment": overall_comment,
                    "is_deleted": False,
                },
            )

            logger.info(
                f"人工评分完成: submission_id={submission_id}, "
                f"score={total_score}, teacher_id={teacher.id}"
            )

            return True, "人工评分完成", grade

        except Exception as e:
            logger.error(f"人工评分失败: {str(e)}", exc_info=True)
            return False, f"人工评分失败: {str(e)}", None
