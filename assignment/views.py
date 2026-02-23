#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: views.py
@Author: kkonggwu
@Date: 2026/2/21
@Version: 1.0
"""
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from utils.api_response import ApiResponse
from .serializers import (
    AssignmentCreateSerializer,
    AssignmentUpdateSerializer,
    AssignmentDetailSerializer,
    AssignmentListSerializer,
    SubmitAnswersSerializer,
    SubmissionListSerializer,
    SubmissionDetailSerializer,
)
from assignment.services.assignment_service import AssignmentService
from assignment.services.grading_service import GradingService



class AssignmentCreateView(APIView):
    """创建作业"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AssignmentCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return JsonResponse({"success": False, "message": "参数错误", "data": serializer.errors}, status=400)

        success, message, assignment = AssignmentService.create_assignment(
            teacher=request.user,
            data=request.data
        )
        if not success:
            return ApiResponse.error(message)
        data = AssignmentDetailSerializer(assignment).data
        return ApiResponse.success(data=data, message=message)

class AssignmentListView(APIView):
    """作业列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        course_id = request.query_params.get("course_id")

        if not course_id:
            return ApiResponse.error(message="缺少 course_id 参数")

        success, message, assignments = AssignmentService.list_assignments(
            course_id=int(course_id),
            user=request.user
        )
        if not success:
            return ApiResponse.error(message)
        data = AssignmentListSerializer(assignments, many=True).data
        return ApiResponse.success(message=message, data=data)

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
