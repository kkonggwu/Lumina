#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业管理路由配置
"""
from django.urls import path
from assignment.bak.views import (
    AssignmentCreateView,
    AssignmentDetailUpdateView,
    AssignmentDeleteView,
    AssignmentListView,
    AssignmentPublishView,
    SubmitAnswersView,
    AnalyzeStandardAnswersView,
    GradeAllSubmissionsView,
    SubmissionListView,
    MySubmissionView,
)

app_name = 'assignment'

urlpatterns = [
    # ==================== 作业 CRUD ====================

    # 创建作业
    # URL: /api/assignment/
    # 方法: POST
    path('', AssignmentCreateView.as_view(), name='assignment_create'),

    # 作业列表
    # URL: /api/assignment/list/?course_id=1
    # 方法: GET
    path('list/', AssignmentListView.as_view(), name='assignment_list'),

    # 作业详情 / 更新
    # URL: /api/assignment/<id>/
    # 方法: GET / PUT
    path('<int:assignment_id>/', AssignmentDetailUpdateView.as_view(), name='assignment_detail_update'),

    # 删除作业
    # URL: /api/assignment/<id>/delete/
    # 方法: DELETE
    path('<int:assignment_id>/delete/', AssignmentDeleteView.as_view(), name='assignment_delete'),

    # 发布作业
    # URL: /api/assignment/<id>/publish/
    # 方法: POST
    path('<int:assignment_id>/publish/', AssignmentPublishView.as_view(), name='assignment_publish'),

    # ==================== 提交与判题 ====================

    # 学生提交答案
    # URL: /api/assignment/<id>/submit/
    # 方法: POST
    path('<int:assignment_id>/submit/', SubmitAnswersView.as_view(), name='submit_answers'),

    # 预分析标准答案
    # URL: /api/assignment/<id>/analyze/
    # 方法: POST
    path('<int:assignment_id>/analyze/', AnalyzeStandardAnswersView.as_view(), name='analyze_answers'),

    # 批量判题
    # URL: /api/assignment/<id>/grade-all/
    # 方法: POST
    path('<int:assignment_id>/grade-all/', GradeAllSubmissionsView.as_view(), name='grade_all'),

    # 查看所有提交（教师）
    # URL: /api/assignment/<id>/submissions/
    # 方法: GET
    path('<int:assignment_id>/submissions/', SubmissionListView.as_view(), name='submission_list'),

    # 查看我的提交和成绩（学生）
    # URL: /api/assignment/<id>/my-submission/
    # 方法: GET
    path('<int:assignment_id>/my-submission/', MySubmissionView.as_view(), name='my_submission'),
]
