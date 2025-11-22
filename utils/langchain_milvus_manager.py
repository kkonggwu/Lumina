#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: langchain_milvus_manager.py
@Author: kkonggwu
@Date: 2025/11/12
@Version: 1.0
"""
from typing import List, Dict
import time

from langchain_community.vectorstores import Milvus
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from pymilvus import connections, utility
from utils.logger import get_logger

logger = get_logger('langchain_milvus_manager')


class LangChainMilvusManager:
    def __init__(
            self,
            host: str = "localhost",
            port: str = "19530",
            collection_name: str = "documents",
            embedding_model: str = "all-MiniLM-L6-v2",
            drop_old_if_mismatch: bool = True  # 如果schema不匹配，是否删除旧集合
    ):
        self.collection_name = collection_name
        self.host = host
        self.port = port

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

        # 检查并处理集合schema不匹配的问题
        # 如果drop_old_if_mismatch=True，会删除所有现有集合
        self._check_and_fix_collection_schema(drop_old_if_mismatch)

        # 初始化Milvus向量存储
        # 注意：LangChain Milvus会根据第一次插入的文档的metadata键创建字段
        # 如果后续文档的metadata键不同，会导致schema不匹配错误
        # 解决方案：删除旧集合，让LangChain重新创建
        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
            connection_args=self.connection_args,
            drop_old=False,  # 不自动删除，我们手动处理
            auto_id=True
        )

    def _check_and_fix_collection_schema(self, drop_old_if_mismatch: bool):
        """
        检查集合是否存在，如果存在但schema不匹配，则删除并重新创建
        
        Args:
            drop_old_if_mismatch: 如果为True，删除所有现有集合（包括LangChain创建的）
        """
        # 等待Milvus服务就绪，最多重试30次，每次等待2秒
        max_retries = 30
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 检查是否已经连接
                try:
                    connections.get_connection_addr("default")
                    # 已连接，断开后重新连接
                    connections.disconnect("default")
                except:
                    pass
                
                # 连接到Milvus
                connections.connect(
                    "default",
                    host=self.host,
                    port=self.port
                )
                # 连接成功，跳出重试循环
                logger.info(f"✅ 成功连接到Milvus: {self.host}:{self.port}")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Milvus连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}，"
                        f"{retry_delay}秒后重试..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Milvus连接失败，已重试{max_retries}次: {str(e)}")
                    raise
        
        try:
            
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                from pymilvus import Collection
                collection = Collection(self.collection_name)
                schema = collection.schema
                field_names = [field.name for field in schema.fields]
                
                # 检查是否是旧的MilvusManager创建的集合（只有4个字段且包含'document'）
                is_old_schema = len(field_names) == 4 and 'document' in field_names
                
                # 如果drop_old_if_mismatch=True，直接删除集合（不管是什么schema）
                # 这样可以避免LangChain Milvus的schema不匹配问题
                if drop_old_if_mismatch:
                    if is_old_schema:
                        logger.warning(
                            f"检测到集合 {self.collection_name} 使用旧schema（MilvusManager创建），"
                            f"删除以重新创建"
                        )
                    else:
                        logger.warning(
                            f"检测到集合 {self.collection_name} 已存在 "
                            f"(字段数: {len(field_names)})，删除以重新创建"
                        )
                    
                    logger.info(f"删除集合 {self.collection_name}...")
                    utility.drop_collection(self.collection_name)
                    logger.info(f"✅ 已删除集合，LangChain将自动创建新集合")
                else:
                    if is_old_schema:
                        logger.warning(
                            f"检测到集合 {self.collection_name} 使用旧schema，"
                            f"建议设置drop_old_if_mismatch=True以自动删除"
                        )
                    else:
                        logger.info(f"集合 {self.collection_name} 已存在 (字段数: {len(field_names)})")
            
        except Exception as e:
            logger.warning(f"检查集合schema时出错: {str(e)}，将尝试继续初始化")
            # 如果连接失败，尝试断开连接，避免后续问题
            try:
                connections.disconnect("default")
            except:
                pass

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
                'course': doc.page_content,
                'metadata': doc.metadata,
                'score': getattr(doc, 'score', 0.0)  # 有些版本可能有分数
            })

        return results

    def get_retriever(self, **kwargs):
        """获取LangChain标准检索器"""
        return self.vector_store.as_retriever(**kwargs)
    
    def add_documents(self, documents: List[Document]):
        """
        添加文档到向量存储（兼容LangChain接口）
        :param documents: Document对象列表
        :return: 文档ID列表
        """
        doc_ids = self.vector_store.add_documents(documents)
        return doc_ids