#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业管理服务层
处理作业的创建、更新、删除、发布、查询等业务逻辑
"""
from typing import Tuple, Optional, List
from decimal import Decimal

from course.models import Assignment, Course
from user.models import UserModel
from utils.logger import get_logger

logger = get_logger('assignment_service')


class AssignmentService:
    """作业服务类"""

    @staticmethod
    def _check_teacher_permission(user, assignment: Assignment) -> Tuple[bool, str]:
        """检查用户是否为该作业所属课程的教师"""
        # 兼容 JWT TokenUser，对应的真实用户信息从 UserModel 中获取
        if not isinstance(user, UserModel):
            try:
                user = UserModel.objects.get(id=getattr(user, "id", None), is_deleted=UserModel.NOT_DELETED)
            except UserModel.DoesNotExist:
                return False, "用户不存在或未登录", ""
        if user.user_type == UserModel.ADMIN:
            return True, ""
        if user.user_type != UserModel.TEACHER:
            return False, "仅教师和管理员可执行此操作"
        if assignment.teacher_id != user.id:
            return False, "只能操作自己创建的作业"
        return True, ""

    @staticmethod
    def create_assignment(teacher, data: dict) -> Tuple[bool, str, Optional[Assignment]]:
        """
        创建作业
        :param teacher: 当前登录用户（教师）
        :param data: 校验后的请求数据
        :return: (success, message, assignment)
        """
        try:
            # 将 JWT TokenUser 转换为真实的 UserModel
            if not isinstance(teacher, UserModel):
                try:
                    teacher = UserModel.objects.get(id=getattr(teacher, "id", None), is_deleted=UserModel.NOT_DELETED)
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", None

            if teacher.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
                return False, "仅教师和管理员可以创建作业", None

            course_id = data['course_id']
            try:
                course = Course.objects.get(id=course_id, is_deleted=False)
            except Course.DoesNotExist:
                return False, "课程不存在", None

            if teacher.user_type == UserModel.TEACHER and course.teacher_id != teacher.id:
                return False, "只能在自己的课程下创建作业", None

            questions = data['questions']
            for q in questions:
                q.setdefault('answer_keypoints', [])
                q.setdefault('analyzed', False)

            total_score = data.get('total_score')
            if total_score is None:
                total_score = sum(Decimal(str(q.get('score', 0))) for q in questions)

            assignment = Assignment(
                course=course,
                teacher=teacher,
                title=data['title'],
                description=data.get('description', ''),
                questions=questions,
                total_score=total_score,
                start_time=data['start_time'],
                end_time=data['end_time'],
                assignment_status=0,
                is_deleted=False,
            )
            assignment.save()

            logger.info(f"作业创建成功: ID={assignment.id}, 标题={data['title']}, 课程={course_id}")
            return True, "作业创建成功", assignment

        except Exception as e:
            logger.error(f"创建作业失败: {str(e)}", exc_info=True)
            return False, f"创建作业失败: {str(e)}", None

    @staticmethod
    def update_assignment(teacher, assignment_id: int, data: dict) -> Tuple[bool, str, Optional[Assignment]]:
        """
        更新作业（仅草稿状态可更新）
        :param teacher: 当前登录用户
        :param assignment_id: 作业 ID
        :param data: 校验后的请求数据
        :return: (success, message, assignment)
        """
        try:
            try:
                assignment = Assignment.objects.select_related('course').get(
                    id=assignment_id, is_deleted=False
                )
            except Assignment.DoesNotExist:
                return False, "作业不存在", None

            ok, msg = AssignmentService._check_teacher_permission(teacher, assignment)
            if not ok:
                return False, msg, None

            if assignment.assignment_status == 1:
                return False, "已发布的作业不能修改", None

            allowed_fields = ['title', 'description', 'questions', 'total_score', 'start_time', 'end_time']
            for field, value in data.items():
                if field in allowed_fields and value is not None:
                    if field == 'questions':
                        for q in value:
                            q.setdefault('answer_keypoints', [])
                            q.setdefault('analyzed', False)
                    setattr(assignment, field, value)

            assignment.save()
            logger.info(f"作业更新成功: ID={assignment_id}")
            return True, "作业更新成功", assignment

        except Exception as e:
            logger.error(f"更新作业失败: {str(e)}", exc_info=True)
            return False, f"更新作业失败: {str(e)}", None

    @staticmethod
    def delete_assignment(teacher, assignment_id: int) -> Tuple[bool, str]:
        """
        逻辑删除作业
        :param teacher: 当前登录用户
        :param assignment_id: 作业 ID
        :return: (success, message)
        """
        try:
            try:
                assignment = Assignment.objects.get(id=assignment_id, is_deleted=False)
            except Assignment.DoesNotExist:
                return False, "作业不存在"

            ok, msg = AssignmentService._check_teacher_permission(teacher, assignment)
            if not ok:
                return False, msg

            assignment.is_deleted = True
            assignment.save()
            logger.info(f"作业删除成功: ID={assignment_id}")
            return True, "作业删除成功"

        except Exception as e:
            logger.error(f"删除作业失败: {str(e)}", exc_info=True)
            return False, f"删除作业失败: {str(e)}"

    @staticmethod
    def publish_assignment(teacher, assignment_id: int) -> Tuple[bool, str]:
        """
        发布作业（草稿 -> 已发布）
        :param teacher: 当前登录用户
        :param assignment_id: 作业 ID
        :return: (success, message)
        """
        try:
            try:
                assignment = Assignment.objects.get(id=assignment_id, is_deleted=False)
            except Assignment.DoesNotExist:
                return False, "作业不存在"

            ok, msg = AssignmentService._check_teacher_permission(teacher, assignment)
            if not ok:
                return False, msg

            if assignment.assignment_status == 1:
                return False, "作业已经发布"

            questions = assignment.questions or []
            if not questions:
                return False, "作业没有题目，无法发布"
            for q in questions:
                if not q.get('standard_answer'):
                    return False, f"第 {q.get('id', '?')} 题缺少标准答案，无法发布"

            assignment.assignment_status = 1
            assignment.save()
            logger.info(f"作业发布成功: ID={assignment_id}")
            return True, "作业发布成功"

        except Exception as e:
            logger.error(f"发布作业失败: {str(e)}", exc_info=True)
            return False, f"发布作业失败: {str(e)}"

    @staticmethod
    def get_assignment_detail(assignment_id: int) -> Tuple[bool, str, Optional[Assignment]]:
        """
        获取作业详情
        :param assignment_id: 作业 ID
        :return: (success, message, assignment)
        """
        try:
            assignment = Assignment.objects.select_related('course', 'teacher').get(
                id=assignment_id, is_deleted=False
            )
            return True, "获取成功", assignment
        except Assignment.DoesNotExist:
            return False, "作业不存在", None

    @staticmethod
    def list_assignments(course_id, user) -> Tuple[bool, str, List[Assignment]]:
        """
        获取作业列表
        当提供 course_id 时，返回该课程下的作业；否则返回用户可见的全部作业
        教师/管理员：可看所有状态；学生：只能看已发布
        :param course_id: 课程 ID（可选）
        :param user: 当前登录用户
        :return: (success, message, assignments)
        """
        try:
            # 兼容 JWT TokenUser，对应的真实用户信息从 UserModel 中获取
            if not isinstance(user, UserModel):
                try:
                    user = UserModel.objects.get(id=getattr(user, "id", None), is_deleted=UserModel.NOT_DELETED)
                except UserModel.DoesNotExist:
                    return False, "用户不存在或未登录", []

            queryset = Assignment.objects.select_related('course', 'teacher').filter(
                is_deleted=False
            )

            if course_id is not None:
                try:
                    Course.objects.get(id=course_id, is_deleted=False)
                except Course.DoesNotExist:
                    return False, "课程不存在", []
                queryset = queryset.filter(course_id=course_id)

            if user.user_type == UserModel.STUDENT:
                queryset = queryset.filter(assignment_status=1)
            elif user.user_type == UserModel.TEACHER:
                queryset = queryset.filter(teacher=user)

            assignments = list(queryset.order_by('-created_at'))
            return True, "获取成功", assignments

        except Exception as e:
            logger.error(f"获取作业列表失败: {str(e)}", exc_info=True)
            return False, f"获取作业列表失败: {str(e)}", []
