#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程服务层
处理课程创建、更新、删除、查询等业务逻辑
"""
import uuid
import random
import string
from typing import Tuple, Optional, List
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist

from course.models import Course, Enrollment
from user.models import UserModel
from user.user_service import UserService
from utils.logger import get_logger

logger = get_logger('course_service')


class CourseService:
    """课程服务类"""
    
    @staticmethod
    def _generate_invite_code() -> str:
        """
        生成唯一的课程邀请码（8位随机字符串）
        
        Returns:
            str: 邀请码
        """
        while True:
            # 生成8位随机字符串（字母+数字）
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            # 检查是否已存在
            if not Course.objects.filter(invite_code=code, is_deleted=False).exists():
                return code
    
    @staticmethod
    def check_create_permission(user_id: int) -> Tuple[bool, str]:
        """
        检查用户是否有创建课程的权限
        
        Args:
            user_id: 用户ID
        
        Returns:
            tuple: (是否有权限, 错误消息)
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"
        
        # 只有管理员和教师可以创建课程
        if user.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
            return False, "只有管理员和教师可以创建课程"
        
        return True, ""
    
    @staticmethod
    def check_update_permission(user_id: int, course: Course) -> Tuple[bool, str]:
        """
        检查用户是否有更新课程的权限
        
        Args:
            user_id: 用户ID
            course: 课程对象
        
        Returns:
            tuple: (是否有权限, 错误消息)
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"
        
        # 管理员可以更新任何课程，教师只能更新自己创建的课程
        if user.user_type == UserModel.ADMIN:
            return True, ""
        elif user.user_type == UserModel.TEACHER:
            if course.teacher_id != user_id:
                return False, "只能更新自己创建的课程"
            return True, ""
        else:
            return False, "只有管理员和教师可以更新课程"
    
    @staticmethod
    def check_delete_permission(user_id: int, course: Course) -> Tuple[bool, str]:
        """
        检查用户是否有删除课程的权限
        
        Args:
            user_id: 用户ID
            course: 课程对象
        
        Returns:
            tuple: (是否有权限, 错误消息)
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"
        
        # 管理员可以删除任何课程，教师只能删除自己创建的课程
        if user.user_type == UserModel.ADMIN:
            return True, ""
        elif user.user_type == UserModel.TEACHER:
            if course.teacher_id != user_id:
                return False, "只能删除自己创建的课程"
            return True, ""
        else:
            return False, "只有管理员和教师可以删除课程"
    
    @staticmethod
    def create_course(
        teacher_id: int,
        course_name: str,
        course_description: Optional[str] = None,
        cover_image: Optional[str] = None,
        academic_year: Optional[str] = None,
        semester: Optional[int] = None,
        max_students: int = 100,
        is_public: bool = False,
        status: int = 1
    ) -> Tuple[bool, str, Optional[Course]]:
        """
        创建课程
        
        Args:
            teacher_id: 教师ID
            course_name: 课程名称
            course_description: 课程描述
            cover_image: 封面图片URL
            academic_year: 学年
            semester: 学期（1-春季，2-秋季）
            max_students: 最大学生数
            is_public: 是否公开
            status: 状态（0-草稿，1-已发布）
        
        Returns:
            tuple: (是否成功, 消息, Course对象)
        """
        try:
            # 检查权限
            has_permission, error_msg = CourseService.check_create_permission(teacher_id)
            if not has_permission:
                return False, error_msg, None
            
            # 验证教师是否存在
            teacher = UserService.get_user_by_id(teacher_id)
            if not teacher:
                return False, "教师不存在", None
            
            # 验证教师类型
            if teacher.user_type not in [UserModel.ADMIN, UserModel.TEACHER]:
                return False, "指定的用户不是教师或管理员", None
            
            # 生成唯一邀请码
            invite_code = CourseService._generate_invite_code()
            
            # 创建课程
            course = Course(
                teacher_id=teacher_id,
                course_name=course_name,
                course_description=course_description,
                cover_image=cover_image,
                invite_code=invite_code,
                academic_year=academic_year,
                semester=semester,
                max_students=max_students,
                is_public=is_public,
                status=status,
                is_deleted=False
            )
            course.save()
            
            logger.info(f"课程创建成功: {course.id} - {course_name} (教师: {teacher_id})")
            return True, "课程创建成功", course
            
        except IntegrityError as e:
            logger.error(f"创建课程失败（唯一性约束）: {str(e)}")
            return False, "创建课程失败：邀请码冲突", None
        except Exception as e:
            logger.error(f"创建课程失败: {str(e)}", exc_info=True)
            return False, f"创建课程失败: {str(e)}", None
    
    @staticmethod
    def update_course(
        user_id: int,
        course_id: int,
        **kwargs
    ) -> Tuple[bool, str, Optional[Course]]:
        """
        更新课程信息
        
        Args:
            user_id: 操作者ID
            course_id: 课程ID
            **kwargs: 要更新的字段（course_name, course_description等）
        
        Returns:
            tuple: (是否成功, 消息, Course对象)
        """
        try:
            # 获取课程
            try:
                course = Course.objects.get(id=course_id, is_deleted=False)
            except Course.DoesNotExist:
                return False, "课程不存在", None
            
            # 检查权限
            has_permission, error_msg = CourseService.check_update_permission(user_id, course)
            if not has_permission:
                return False, error_msg, None
            
            # 更新字段（排除不允许直接修改的字段）
            allowed_fields = [
                'course_name', 'course_description', 'cover_image',
                'academic_year', 'semester', 'max_students',
                'is_public', 'status'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(course, field, value)
            
            course.save()
            
            logger.info(f"课程更新成功: {course_id} (操作者: {user_id})")
            return True, "课程更新成功", course
            
        except Exception as e:
            logger.error(f"更新课程失败: {str(e)}", exc_info=True)
            return False, f"更新课程失败: {str(e)}", None
    
    @staticmethod
    def delete_course(user_id: int, course_id: int) -> Tuple[bool, str]:
        """
        删除课程（逻辑删除）
        
        Args:
            user_id: 操作者ID
            course_id: 课程ID
        
        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            # 获取课程
            try:
                course = Course.objects.get(id=course_id, is_deleted=False)
            except Course.DoesNotExist:
                return False, "课程不存在"
            
            # 检查权限
            has_permission, error_msg = CourseService.check_delete_permission(user_id, course)
            if not has_permission:
                return False, error_msg
            
            # 逻辑删除
            course.is_deleted = True
            course.save()
            
            logger.info(f"课程删除成功: {course_id} (操作者: {user_id})")
            return True, "课程删除成功"
            
        except Exception as e:
            logger.error(f"删除课程失败: {str(e)}", exc_info=True)
            return False, f"删除课程失败: {str(e)}"
    
    @staticmethod
    def get_course(course_id: int, user_id: Optional[int] = None) -> Optional[Course]:
        """
        获取课程详情
        
        Args:
            course_id: 课程ID
            user_id: 用户ID（可选，用于权限检查）
        
        Returns:
            Course对象，如果不存在返回None
        """
        try:
            course = Course.objects.select_related('teacher').get(
                id=course_id,
                is_deleted=False
            )
            return course
        except Course.DoesNotExist:
            return None
    
    @staticmethod
    def list_courses(
        teacher_id: Optional[int] = None,
        status: Optional[int] = None,
        is_public: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        user=None,
        mine: bool = False
    ) -> Tuple[List[Course], int]:
        """
        获取课程列表
        
        Args:
            teacher_id: 教师ID（可选，用于筛选）
            status: 状态（可选，用于筛选）
            is_public: 是否公开（可选，用于筛选）
            limit: 返回数量限制
            offset: 偏移量
            user: 当前用户（mine=True 时使用）
            mine: 是否只返回当前用户有权限管理/参与的课程
        
        Returns:
            tuple: (课程列表, 总数量)
        """
        try:
            query = Course.objects.select_related('teacher').filter(is_deleted=False)

            if mine and user is not None:
                if not isinstance(user, UserModel):
                    try:
                        user = UserModel.objects.get(
                            id=getattr(user, "id", None),
                            is_deleted=UserModel.NOT_DELETED,
                        )
                    except UserModel.DoesNotExist:
                        return [], 0

                if user.user_type == UserModel.TEACHER:
                    query = query.filter(teacher_id=user.id)
                elif user.user_type == UserModel.STUDENT:
                    enrolled_course_ids = Enrollment.objects.filter(
                        student=user,
                        enrollment_status=1,
                        is_deleted=False,
                    ).values_list('course_id', flat=True)
                    query = query.filter(id__in=enrolled_course_ids, status=1)
                # 管理员 mine=true 时仍返回全部课程，便于代管。
            
            # 按教师筛选
            if teacher_id:
                query = query.filter(teacher_id=teacher_id)
            
            # 按状态筛选
            if status is not None:
                query = query.filter(status=status)
            
            # 按是否公开筛选
            if is_public is not None:
                query = query.filter(is_public=is_public)
            
            # 计算总数
            total = query.count()
            
            # 分页，按创建时间倒序
            courses = query.order_by('-created_at')[offset:offset + limit]
            
            return list(courses), total
            
        except Exception as e:
            logger.error(f"获取课程列表失败: {str(e)}", exc_info=True)
            return [], 0


class EnrollmentService:
    """选课服务类"""
    
    @staticmethod
    def join_course_by_invite_code(student_id: int, invite_code: str) -> Tuple[bool, str, Optional[Enrollment]]:
        """
        学生通过邀请码加入课程
        
        Args:
            student_id: 学生ID
            invite_code: 课程邀请码
        
        Returns:
            tuple: (是否成功, 消息, Enrollment对象)
        """
        try:
            # 验证学生是否存在
            student = UserService.get_user_by_id(student_id)
            if not student:
                return False, "学生不存在", None
            
            # 验证学生类型
            if student.user_type != UserModel.STUDENT:
                return False, "只有学生可以加入课程", None
            
            # 查找课程
            try:
                course = Course.objects.get(invite_code=invite_code, is_deleted=False)
            except Course.DoesNotExist:
                return False, "邀请码无效或课程不存在", None
            
            # 检查课程状态
            if course.status == 0:  # 草稿状态
                return False, "课程尚未发布，无法加入", None
            
            # 检查是否已经加入
            existing_enrollment = Enrollment.objects.filter(
                course_id=course.id,
                student_id=student_id,
                is_deleted=False
            ).first()
            
            if existing_enrollment:
                if existing_enrollment.enrollment_status == 1:  # 已加入
                    return False, "您已经加入该课程", None
                elif existing_enrollment.enrollment_status == 0:  # 待审核
                    return False, "您的加入申请正在审核中", None
            
            # 检查课程人数是否已满
            current_enrollments = Enrollment.objects.filter(
                course_id=course.id,
                enrollment_status=1,  # 已加入
                is_deleted=False
            ).count()
            
            if current_enrollments >= course.max_students:
                return False, "课程人数已满", None
            
            # 创建选课记录
            enrollment = Enrollment(
                course_id=course.id,
                student_id=student_id,
                enrollment_status=1,  # 默认已加入（如果课程需要审核，可以改为0-待审核）
                is_deleted=False
            )
            enrollment.save()
            
            logger.info(f"学生 {student_id} 成功加入课程 {course.id} (邀请码: {invite_code})")
            return True, "成功加入课程", enrollment
            
        except IntegrityError:
            return False, "您已经加入该课程", None
        except Exception as e:
            logger.error(f"加入课程失败: {str(e)}", exc_info=True)
            return False, f"加入课程失败: {str(e)}", None
    
    @staticmethod
    def leave_course(student_id: int, course_id: int) -> Tuple[bool, str]:
        """
        学生退出课程
        
        Args:
            student_id: 学生ID
            course_id: 课程ID
        
        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            # 验证学生是否存在
            student = UserService.get_user_by_id(student_id)
            if not student:
                return False, "学生不存在"
            
            # 查找选课记录
            try:
                enrollment = Enrollment.objects.get(
                    course_id=course_id,
                    student_id=student_id,
                    is_deleted=False
                )
            except Enrollment.DoesNotExist:
                return False, "您未加入该课程"
            
            # 更新状态为已退出（逻辑删除）
            enrollment.enrollment_status = 2  # 已退出
            enrollment.is_deleted = True
            enrollment.save()
            
            logger.info(f"学生 {student_id} 退出课程 {course_id}")
            return True, "成功退出课程"
            
        except Exception as e:
            logger.error(f"退出课程失败: {str(e)}", exc_info=True)
            return False, f"退出课程失败: {str(e)}"
    
    @staticmethod
    def get_course_students(
        course_id: int,
        enrollment_status: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Enrollment], int]:
        """
        获取课程的学生列表
        
        Args:
            course_id: 课程ID
            enrollment_status: 选课状态（可选，用于筛选）
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            tuple: (选课记录列表, 总数量)
        """
        try:
            query = Enrollment.objects.select_related('student', 'course').filter(
                course_id=course_id,
                is_deleted=False
            )
            
            # 按选课状态筛选
            if enrollment_status is not None:
                query = query.filter(enrollment_status=enrollment_status)
            
            # 计算总数
            total = query.count()
            
            # 分页，按加入时间倒序
            enrollments = query.order_by('-joined_at')[offset:offset + limit]
            
            return list(enrollments), total
            
        except Exception as e:
            logger.error(f"获取课程学生列表失败: {str(e)}", exc_info=True)
            return [], 0
    
    @staticmethod
    def get_student_courses(
        student_id: int,
        enrollment_status: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Enrollment], int]:
        """
        获取学生的选课列表
        
        Args:
            student_id: 学生ID
            enrollment_status: 选课状态（可选，用于筛选）
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            tuple: (选课记录列表, 总数量)
        """
        try:
            query = Enrollment.objects.select_related('course', 'course__teacher').filter(
                student_id=student_id,
                is_deleted=False
            )
            
            # 按选课状态筛选
            if enrollment_status is not None:
                query = query.filter(enrollment_status=enrollment_status)
            
            # 计算总数
            total = query.count()
            
            # 分页，按加入时间倒序
            enrollments = query.order_by('-joined_at')[offset:offset + limit]
            
            return list(enrollments), total
            
        except Exception as e:
            logger.error(f"获取学生选课列表失败: {str(e)}", exc_info=True)
            return [], 0
    
    @staticmethod
    def check_enrollment(student_id: int, course_id: int) -> Optional[Enrollment]:
        """
        检查学生是否已加入课程
        
        Args:
            student_id: 学生ID
            course_id: 课程ID
        
        Returns:
            Enrollment对象，如果未加入返回None
        """
        try:
            return Enrollment.objects.get(
                course_id=course_id,
                student_id=student_id,
                enrollment_status=1,  # 已加入
                is_deleted=False
            )
        except Enrollment.DoesNotExist:
            return None

