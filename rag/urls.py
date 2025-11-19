#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: urls.py
@Author: kkonggwu
@Date: 2025/11/10
@Version: 1.0
"""
from django.urls import path
from .views import ChatView, ChatHistoryView, ChatRagView

app_name = 'rag'

urlpatterns = [
    # 普通问答接口
    # URL: /api/rag/chat/
    # 方法: POST
    path('chat/', ChatView.as_view(), name='chat'),

    # 获取问答历史接口
    # URL: /api/rag/history/?session_id=xxx&course_id=1&limit=10
    # 方法: GET
    path('history/', ChatHistoryView.as_view(), name='chat_history'),

    # RAG 问答
    # URL: /api/rag/chat_rag/
    # 方法: POST
    path('chat_rag',ChatRagView.as_view(), name='chat_rag'),
]