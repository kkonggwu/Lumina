#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: langchain_milvus_manager.py
@Author: kkonggwu
@Date: 2025/11/12
@Version: 1.0
"""
from typing import List, Dict

from langchain_community.vectorstores import Milvus
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


class LangChainMilvusManager:
    def __init__(
            self,
            host: str = "localhost",
            port: str = "19530",
            collection_name: str = "documents",
            embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.collection_name = collection_name

        # 使用LangChain的嵌入模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'}
        )

        # 连接参数
        self.connection_args = {
            "host": host,
            "port": port
        }

        # 初始化Milvus向量存储
        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
            connection_args=self.connection_args,
            drop_old=False,  # 生产环境设为False
            auto_id=True
        )

    def insert_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """使用LangChain插入文档"""
        if metadatas is None:
            metadatas = [{} for _ in documents]

        # 创建Document对象
        docs = [
            Document(page_content=doc, metadata=meta)
            for doc, meta in zip(documents, metadatas)
        ]

        # 使用LangChain添加文档（自动处理向量化）
        doc_ids = self.vector_store.add_documents(docs)
        return doc_ids

    def search_similar(self, query: str, limit: int = 5):
        """使用LangChain检索"""
        # 创建标准检索器
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": limit}
        )

        # 检索文档
        docs = retriever.get_relevant_documents(query)

        # 格式化结果
        results = []
        for doc in docs:
            results.append({
                'document': doc.page_content,
                'metadata': doc.metadata,
                'score': getattr(doc, 'score', 0.0)  # 有些版本可能有分数
            })

        return results

    def get_retriever(self, **kwargs):
        """获取LangChain标准检索器"""
        return self.vector_store.as_retriever(**kwargs)