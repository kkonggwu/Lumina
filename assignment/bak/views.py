#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业管理视图
"""
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from assignment.serializers import (
    AssignmentCreateSerializer,
    AssignmentUpdateSerializer,
    AssignmentDetailSerializer,
    AssignmentListSerializer,
    SubmitAnswersSerializer,
    SubmissionListSerializer,
    SubmissionDetailSerializer,
    ManualGradeSerializer,
    QuestionKeypointsUpdateSerializer,
)
from assignment.services.assignment_service import AssignmentService
from assignment.services.grading_service import GradingService


# ==================== 作业 CRUD ====================

class AssignmentCreateView(APIView):
    """创建作业"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AssignmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({"success": False, "message": "参数错误", "data": serializer.errors}, status=400)

        success, message, assignment = AssignmentService.create_assignment(
            teacher=request.user,
            data=serializer.validated_data,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)

        data = AssignmentDetailSerializer(assignment).data
        return JsonResponse({"success": True, "message": message, "data": data})


class AssignmentListView(APIView):
    """作业列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        course_id = request.query_params.get('course_id')

        success, message, assignments = AssignmentService.list_assignments(
            course_id=int(course_id) if course_id else None,
            user=request.user,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)

        data = AssignmentListSerializer(assignments, many=True).data
        return JsonResponse({"success": True, "message": message, "data": data})


class AssignmentDetailUpdateView(APIView):
    """作业详情 / 更新"""
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id):
        success, message, assignment = AssignmentService.get_assignment_detail(assignment_id)
        if not success:
            return JsonResponse({"success": False, "message": message}, status=404)

        data = AssignmentDetailSerializer(assignment).data
        return JsonResponse({"success": True, "message": message, "data": data})

    def put(self, request, assignment_id):
        serializer = AssignmentUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({"success": False, "message": "参数错误", "data": serializer.errors}, status=400)

        success, message, assignment = AssignmentService.update_assignment(
            teacher=request.user,
            assignment_id=assignment_id,
            data=serializer.validated_data,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)

        data = AssignmentDetailSerializer(assignment).data
        return JsonResponse({"success": True, "message": message, "data": data})


class AssignmentDeleteView(APIView):
    """删除作业"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, assignment_id):
        success, message = AssignmentService.delete_assignment(
            teacher=request.user,
            assignment_id=assignment_id,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)
        return JsonResponse({"success": True, "message": message})


class AssignmentPublishView(APIView):
    """发布作业"""
    permission_classes = [IsAuthenticated]

    def post(self, request, assignment_id):
        success, message = AssignmentService.publish_assignment(
            teacher=request.user,
            assignment_id=assignment_id,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)
        return JsonResponse({"success": True, "message": message})


class QuestionKeypointsUpdateView(APIView):
    """
    更新单个题目的标准答案关键点（教师端手工编辑）

    URL: /api/assignment/<assignment_id>/questions/<question_id>/keypoints/
    方法: PUT
    请求体示例:
    {
      "keypoints": ["关键点1", "关键点2", ...]
    }
    """

    permission_classes = [IsAuthenticated]

    def put(self, request, assignment_id, question_id):
        serializer = QuestionKeypointsUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse(
                {
                    "success": False,
                    "message": "参数错误",
                    "data": serializer.errors,
                },
                status=400,
            )

        keypoints = serializer.validated_data["keypoints"]

        success, message, assignment = AssignmentService.update_question_keypoints(
            teacher=request.user,
            assignment_id=assignment_id,
            question_id=question_id,
            keypoints=keypoints,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)

        # 返回最新的整个作业 questions，方便前端刷新视图
        data = AssignmentDetailSerializer(assignment).data
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "data": data,
            }
        )


# ==================== 提交与判题 ====================

class SubmitAnswersView(APIView):
    """学生提交答案"""
    permission_classes = [IsAuthenticated]

    def post(self, request, assignment_id):
        serializer = SubmitAnswersSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({"success": False, "message": "参数错误", "data": serializer.errors}, status=400)

        success, message, submission = GradingService.submit_answers(
            assignment_id=assignment_id,
            student=request.user,
            answers=serializer.validated_data['answers'],
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)

        return JsonResponse({"success": True, "message": message, "data": {"submission_id": submission.id}})


class AnalyzeStandardAnswersView(APIView):
    """预分析标准答案"""
    permission_classes = [IsAuthenticated]

    def post(self, request, assignment_id):
        success, message, data = GradingService.analyze_standard_answers(
            assignment_id=assignment_id,
            teacher=request.user,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)
        return JsonResponse({"success": True, "message": message, "data": data})


class GradeAllSubmissionsView(APIView):
    """批量判题"""
    permission_classes = [IsAuthenticated]

    def post(self, request, assignment_id):
        success, message, data = GradingService.grade_all_submissions(
            assignment_id=assignment_id,
            teacher=request.user,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)
        return JsonResponse({"success": True, "message": message, "data": data})


class SubmissionListView(APIView):
    """查看所有提交（教师）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id):
        success, message, submissions = GradingService.get_submissions(
            assignment_id=assignment_id,
            teacher=request.user,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)

        data = SubmissionListSerializer(submissions, many=True).data
        return JsonResponse({"success": True, "message": message, "data": data})


class MySubmissionView(APIView):
    """查看我的提交和成绩（学生）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id):
        success, message, submission = GradingService.get_my_submission(
            assignment_id=assignment_id,
            student=request.user,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=404)

        data = SubmissionDetailSerializer(submission).data
        return JsonResponse({"success": True, "message": message, "data": data})


class TeacherSubmissionDetailView(APIView):
    """
    教师查看指定提交的详情（含评分信息），用于评分报告界面。

    URL: /api/assignment/<assignment_id>/submissions/<submission_id>/
    方法: GET
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id, submission_id):
        success, message, submission = GradingService.get_submission_detail_for_teacher(
            assignment_id=assignment_id,
            submission_id=submission_id,
            teacher=request.user,
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=404)

        data = SubmissionDetailSerializer(submission).data
        return JsonResponse({"success": True, "message": message, "data": data})


class ManualGradeSubmissionView(APIView):
    """
    教师人工评分单个提交

    URL: /api/assignment/<assignment_id>/submissions/<submission_id>/manual-grade/
    方法: POST
    请求体:
    {
      "total_score": 8.5,
      "grading_rubric": [...],   # 可选，JSON
      "overall_comment": "老师的总体评语"  # 可选
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, assignment_id, submission_id):
        serializer = ManualGradeSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse(
                {
                    "success": False,
                    "message": "参数错误",
                    "data": serializer.errors,
                },
                status=400,
            )

        data = serializer.validated_data
        success, message, grade = GradingService.manual_grade_submission(
            submission_id=submission_id,
            teacher=request.user,
            total_score=data["total_score"],
            grading_rubric=data.get("grading_rubric"),
            overall_comment=data.get("overall_comment", ""),
        )
        if not success:
            return JsonResponse({"success": False, "message": message}, status=400)

        # 返回简单的评分结果摘要，前端可根据需要再调用 SubmissionList / Detail
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "data": {
                    "submission_id": submission_id,
                    "total_score": str(grade.submission.total_score),
                    "overall_comment": grade.overall_comment,
                },
            }
        )
