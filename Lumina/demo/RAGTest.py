#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: RAGTest.py
@Author: kkonggwu
@Date: 2025/11/16
@Version: 1.0
"""
from utils.rag_module import RagModule, create_rag_pipeline

# 方式1：标准初始化
rag = RagModule()
rag.initialize_system()
rag.load_and_process_documents()
rag.index_documents()
result = rag.process_query("您的问题")

# 方式2：使用上下文管理器
with RagModule() as rag:
    rag.load_and_process_documents()
    rag.index_documents()
    result = rag.process_query("您的问题")

# 方式3：使用便捷函数
rag = create_rag_pipeline(data_path="your_data_path")
rag.load_and_process_documents()
rag.index_documents()
result = rag.process_query("您的问题")