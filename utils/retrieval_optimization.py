#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: retrieval_optimization.py
@Author: kkonggwu
@Date: 2025/11/15
@Version: 1.0
"""
from typing import List, Dict, Any

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from utils.langchain_milvus_manager import LangChainMilvusManager
from utils.logger import get_logger

logger = get_logger('retrieval_optimization')


class RetrievalOptimization:
    def __init__(self, vectorstore, chunks: List[Document], vectorstore_type: str = "milvus"):
        """
        初始化检索优化模块
        :param vectorstore: 向量存储实例
        :param chunks: 文档块列表
        :param vectorstore_type: 向量存储类型
        """

        self.bm25_retriever = None
        self.vector_retriever = None
        self.vectorstore = vectorstore
        self.chunks = chunks
        self.vectorstore_type = vectorstore_type
        self.setup_retrievers()

    def setup_retrievers(self):
        """设置向量检索器和BM25检索器"""
        logger.info("正在设置检索器...")

        # 向量检索器 - 使用as_retriever方法
        self.vector_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )

        # BM25检索器（如果chunks为空，则不创建BM25检索器）
        if self.chunks and len(self.chunks) > 0:
            self.bm25_retriever = BM25Retriever.from_documents(
                self.chunks,
                k=5
            )
            logger.info("BM25检索器已创建")
        else:
            self.bm25_retriever = None
            logger.info("BM25检索器未创建（chunks为空，文档通过上传接口动态添加）")

        logger.info("检索器设置完成")
        
    def hybrid_search(self, query: str, top_k: int = 3, similarity_threshold: float = None) -> List[Document]:
        """
        混合检索（如果BM25检索器不可用，则仅使用向量检索）
        :param query: 查询文本
        :param top_k: 返回结果数量
        :param similarity_threshold: 相似度阈值，低于此值的文档将被过滤（0-1之间，None表示不过滤）
        :return: 检索到的文档列表
        """
        # 使用向量检索器
        vector_docs = self.vector_retriever.get_relevant_documents(query)
        
        # 如果BM25检索器可用，进行混合检索
        if self.bm25_retriever is not None:
            bm25_docs = self.bm25_retriever.get_relevant_documents(query)
            reranked_docs = self._rrf_rerank(vector_docs, bm25_docs)
            filtered_docs = reranked_docs[:top_k]
        else:
            # 如果BM25检索器不可用，仅使用向量检索结果
            logger.debug("BM25检索器不可用，仅使用向量检索")
            filtered_docs = vector_docs[:top_k]
        
        # 应用相似度阈值过滤
        if similarity_threshold is not None and similarity_threshold > 0:
            filtered_docs = self._filter_by_similarity(filtered_docs, similarity_threshold)
            logger.info(f"应用相似度阈值 {similarity_threshold}，过滤后剩余 {len(filtered_docs)} 个文档")
        
        return filtered_docs
    
    def _filter_by_similarity(self, docs: List[Document], threshold: float) -> List[Document]:
        """
        根据相似度分数过滤文档
        :param docs: 文档列表
        :param threshold: 相似度阈值（0-1之间）
        :return: 过滤后的文档列表
        """
        filtered = []
        for doc in docs:
            score = None
            
            # 方法1: 尝试从文档的metadata中获取相似度分数
            # LangChain检索器可能会在metadata中存储score
            if 'score' in doc.metadata:
                score = doc.metadata.get('score')
                logger.debug(f"从metadata.score获取相似度: {score:.4f}")
            
            # 方法2: 如果没有score，尝试从rrf_score获取
            elif 'rrf_score' in doc.metadata:
                score = doc.metadata.get('rrf_score')
                logger.debug(f"从metadata.rrf_score获取相似度: {score:.4f}")
            
            # 方法3: 尝试从文档对象的属性获取（LangChain可能直接设置）
            elif hasattr(doc, 'score') and doc.score is not None:
                score = doc.score
                logger.debug(f"从doc.score获取相似度: {score:.4f}")
            
            # 方法4: 尝试从distance计算（distance越小，相似度越高）
            elif hasattr(doc, 'distance') and doc.distance is not None:
                # distance是距离，需要转换为相似度分数
                # 使用简单的转换：similarity = 1 / (1 + distance)
                # 对于L2距离，通常范围在0-2之间，这里归一化到0-1
                distance = doc.distance
                score = 1.0 / (1.0 + distance)
                logger.debug(f"从distance计算相似度: distance={distance:.4f}, score={score:.4f}")
            
            # 方法5: 尝试从metadata中获取distance并转换
            elif 'distance' in doc.metadata:
                distance = doc.metadata.get('distance')
                score = 1.0 / (1.0 + distance)
                logger.debug(f"从metadata.distance计算相似度: distance={distance:.4f}, score={score:.4f}")
            
            # 判断是否保留文档
            if score is None:
                # 如果没有分数，记录警告但默认保留（避免误过滤）
                logger.warning(f"文档没有相似度分数，无法过滤，默认保留: {doc.page_content[:50]}...")
                filtered.append(doc)
            elif score >= threshold:
                filtered.append(doc)
                logger.debug(f"文档相似度分数 {score:.4f} >= 阈值 {threshold}，保留")
            else:
                logger.info(f"文档相似度分数 {score:.4f} < 阈值 {threshold}，已过滤")
        
        logger.info(f"相似度过滤: 原始文档数={len(docs)}, 过滤后文档数={len(filtered)}, 阈值={threshold}")
        return filtered

    def metadata_filtered_search(self, query: str, filters: Dict[str, Any], top_k: int = 5, similarity_threshold: float = None) -> List[Document]:
        """
        带元数据过滤的检索
        :param query: 查询文本
        :param filters: 元数据过滤条件
        :param top_k: 返回结果数量
        :param similarity_threshold: 相似度阈值，低于此值的文档将被过滤（0-1之间，None表示不过滤）
        :return: 过滤后的文档列表
        """

        # 先进行混合检索，获取更多候选（应用相似度阈值）
        docs = self.hybrid_search(query, top_k * 3, similarity_threshold)

        # 应用元数据过滤
        filtered_docs = []
        for doc in docs:
            match = True
            for key, value in filters.items():
                if key in doc.metadata:
                    if isinstance(value, list):
                        if doc.metadata[key] not in value:
                            match = False
                            break
                    else:
                        if doc.metadata[key] != value:
                            match = False
                            break
                else:
                    match = False
                    break

            if match:
                filtered_docs.append(doc)
                if len(filtered_docs) >= top_k:
                    break

        return filtered_docs

    @staticmethod
    def _rrf_rerank(vector_docs: List[Document], bm25_docs: List[Document], k: int = 60) -> List[Document]:
        """
        使用RRF (Reciprocal Rank Fusion) 算法重排文档

        Args:
            vector_docs: 向量检索结果
            bm25_docs: BM25检索结果
            k: RRF参数，用于平滑排名

        Returns:
            重排后的文档列表
        """
        doc_scores = {}
        doc_objects = {}

        # 计算向量检索结果的RRF分数
        for rank, doc in enumerate(vector_docs):
            # 使用文档内容的哈希作为唯一标识
            doc_id = hash(doc.page_content)
            doc_objects[doc_id] = doc

            # RRF公式: 1 / (k + rank)
            rrf_score = 1.0 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

            logger.debug(f"向量检索 - 文档{rank + 1}: RRF分数 = {rrf_score:.4f}")

        # 计算BM25检索结果的RRF分数
        for rank, doc in enumerate(bm25_docs):
            doc_id = hash(doc.page_content)
            doc_objects[doc_id] = doc

            rrf_score = 1.0 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

            logger.debug(f"BM25检索 - 文档{rank + 1}: RRF分数 = {rrf_score:.4f}")

        # 按最终RRF分数排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建最终结果
        reranked_docs = []
        for doc_id, final_score in sorted_docs:
            if doc_id in doc_objects:
                doc = doc_objects[doc_id]
                # 将RRF分数添加到文档元数据中
                doc.metadata['rrf_score'] = final_score
                reranked_docs.append(doc)
                logger.debug(f"最终排序 - 文档: {doc.page_content[:50]}... 最终RRF分数: {final_score:.4f}")

        logger.info(
            f"RRF重排完成: 向量检索{len(vector_docs)}个文档, BM25检索{len(bm25_docs)}个文档, 合并后{len(reranked_docs)}个文档")

        return reranked_docs
