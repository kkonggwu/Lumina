#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档管理路由配置
"""
from django.urls import path
from .views import (
    # 文档管理视图
    DocumentUploadView,
    DocumentDeleteView,
    DocumentDownloadView,
    DocumentDetailView,
    DocumentListView,
    # 课程管理视图
    CourseListCreateView,
    CourseDetailUpdateView,
    CourseDeleteView,
    # 选课管理视图
    EnrollmentJoinView,
    EnrollmentLeaveView,
    CourseStudentsView,
    StudentCoursesView
)

app_name = 'course'

urlpatterns = [
    # 文档上传接口
    # URL: /api/course/documents/upload/
    # 方法: POST
    path('documents/upload/', DocumentUploadView.as_view(), name='document_upload'),
    
    # 文档删除接口
    # URL: /api/course/documents/<document_id>/delete/
    # 方法: DELETE
    path('documents/<int:document_id>/delete/', DocumentDeleteView.as_view(), name='document_delete'),
    
    # 文档下载接口
    # URL: /api/course/documents/<document_id>/download/
    # 方法: GET
    path('documents/<int:document_id>/download/', DocumentDownloadView.as_view(), name='document_download'),
    
    # 文档详情接口
    # URL: /api/course/documents/<document_id>/
    # 方法: GET
    path('documents/<int:document_id>/', DocumentDetailView.as_view(), name='document_detail'),
    
    # 文档列表接口
    # URL: /api/course/documents/?course_id=1&page=1&page_size=20
    # 方法: GET
    path('documents/', DocumentListView.as_view(), name='document_list'),
    
    # ==================== 课程管理路由 ====================
    
    # 课程列表和创建接口
    # URL: /api/course/courses/
    # 方法: GET (列表), POST (创建)
    path('courses/', CourseListCreateView.as_view(), name='course_list_create'),
    
    # 课程详情和更新接口
    # URL: /api/course/courses/<course_id>/
    # 方法: GET (详情), PUT (更新)
    path('courses/<int:course_id>/', CourseDetailUpdateView.as_view(), name='course_detail_update'),
    
    # 删除课程接口
    # URL: /api/course/courses/<course_id>/delete/
    # 方法: DELETE
    path('courses/<int:course_id>/delete/', CourseDeleteView.as_view(), name='course_delete'),
    
    # ==================== 选课管理路由 ====================
    
    # 加入课程接口
    # URL: /api/course/enrollments/join/
    # 方法: POST
    path('enrollments/join/', EnrollmentJoinView.as_view(), name='enrollment_join'),
    
    # 退出课程接口
    # URL: /api/course/enrollments/<course_id>/leave/
    # 方法: DELETE
    path('enrollments/<int:course_id>/leave/', EnrollmentLeaveView.as_view(), name='enrollment_leave'),
    
    # 课程学生列表接口
    # URL: /api/course/courses/<course_id>/students/?enrollment_status=1&page=1&page_size=50
    # 方法: GET
    path('courses/<int:course_id>/students/', CourseStudentsView.as_view(), name='course_students'),
    
    # 学生选课列表接口
    # URL: /api/course/enrollments/?enrollment_status=1&page=1&page_size=20
    # 方法: GET
    path('enrollments/', StudentCoursesView.as_view(), name='student_courses'),
]



