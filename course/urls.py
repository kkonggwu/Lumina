#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档管理路由配置
"""
from django.urls import path
from .views import (
    DocumentUploadView,
    DocumentDeleteView,
    DocumentDownloadView,
    DocumentDetailView,
    DocumentListView
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
]



