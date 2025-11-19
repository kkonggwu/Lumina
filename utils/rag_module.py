#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: rag_module.py
@Author: kkonggwu
@Date: 2025/11/16
@Version: 2.0
"""
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from config.config import APIConfig, DASHSCOPE_API_KEY
from utils.ai_handler import AIHandler
from utils.data_processor import DataProcessor
from utils.langchain_milvus_manager import LangChainMilvusManager
from utils.retrieval_optimization import RetrievalOptimization
from utils.logger import get_logger

logger = get_logger('rag_module')


class RagModule:
    def __init__(self):
        """初始化RAG系统模块"""
        self.config = APIConfig.get_config("qwen")
        self.api_key = DASHSCOPE_API_KEY
        self.data_processor = None
        self.milvus_manager = None
        self.retrieval_module = None
        self.generation_module = None
        self.initialized = False
        self.chunks = []
        
        # 检索配置
        self.retrieval_config = {
            "top_k": 3,
            "rerank_k": 60,
            "chunk_size": 1000,
            "chunk_overlap": 200
        }

        # 检查数据路径和API密钥
        data_path = self.config["data_path"]
        # 确保 data_path 是 Path 对象
        if isinstance(data_path, str):
            from pathlib import Path
            data_path = Path(data_path)
        self.config["data_path"] = data_path

        if not data_path.exists():
            raise FileNotFoundError(f"数据路径不存在: {data_path}")
        if not DASHSCOPE_API_KEY:
            raise ValueError("请设置 API_KEY 环境变量")

    def initialize_system(self):
        """初始化所有模块"""
        logger.info("开始初始化RAG系统...")
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.config["data_path"])
        logger.info("数据处理器初始化完成")
        
        # 初始化Milvus管理器
        self.milvus_manager = LangChainMilvusManager()
        logger.info("Milvus管理器初始化完成")
        
        # 初始化AI处理器
        self.generation_module = AIHandler(
            api_key=self.api_key,
            api_base=self.config["api_base"]
        )
        logger.info("AI处理器初始化完成")
        
        self.initialized = True
        logger.info("RAG系统初始化完成")
    
    def load_and_process_documents(self) -> List[Document]:
        """
        加载并处理文档
        :return: 处理后的文档块列表
        """
        if not self.initialized:
            self.initialize_system()
        
        logger.info("开始加载和处理文档...")
        
        # 加载文档
        documents = self.data_processor.load_documents()
        logger.info(f"加载了 {len(documents)} 个文档")
        
        # 分块文档（DataProcessor的chunk_documents方法不接受参数）
        self.chunks = self.data_processor.chunk_documents()
        logger.info(f"文档分块完成，共 {len(self.chunks)} 个块")
        
        # 增强块的元数据（如果还没有chunk_id）
        for i, chunk in enumerate(self.chunks):
            if "chunk_id" not in chunk.metadata:
                chunk.metadata["chunk_id"] = i
        
        return self.chunks
    
    def index_documents(self, chunks: Optional[List[Document]] = None):
        """
        将文档块索引到向量数据库
        :param chunks: 文档块列表，如果为None则使用已加载的块
        """
        if not self.initialized:
            self.initialize_system()
        
        if chunks is None:
            if not self.chunks:
                chunks = self.load_and_process_documents()
            else:
                chunks = self.chunks
        
        logger.info(f"开始索引 {len(chunks)} 个文档块...")
        
        # 将文档块添加到向量存储
        self.milvus_manager.add_documents(chunks)
        logger.info("文档索引完成")
        
        # 初始化检索优化模块
        self.retrieval_module = RetrievalOptimization(
            vectorstore=self.milvus_manager.vector_store,
            chunks=chunks
        )
        logger.info("检索优化模块初始化完成")
    
    def retrieve_documents(self, query: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 3) -> List[Document]:
        """
        根据查询检索相关文档
        :param query: 查询文本
        :param filters: 元数据过滤条件
        :param top_k: 返回结果数量
        :return: 检索到的文档列表
        """
        if not self.retrieval_module:
            raise ValueError("检索模块未初始化，请先调用index_documents方法")
        
        logger.info(f"开始检索文档，查询: {query[:50]}...")
        
        if filters:
            # 使用带元数据过滤的检索
            docs = self.retrieval_module.metadata_filtered_search(query, filters, top_k)
        else:
            # 使用混合检索
            docs = self.retrieval_module.hybrid_search(query, top_k)
        
        logger.info(f"检索完成，找到 {len(docs)} 个相关文档")
        return docs
    
    def generate_response(self, query: str, retrieved_docs: List[Document], use_stream: bool = False) -> str:
        """
        根据检索到的文档生成回复
        :param query: 查询文本
        :param retrieved_docs: 检索到的文档列表
        :param use_stream: 是否使用流式响应（当前版本暂不支持，将使用非流式）
        :return: 生成的回复
        """
        if not self.initialized:
            self.initialize_system()
        
        if not retrieved_docs:
            logger.warning("没有检索到相关文档，将返回空回复")
            return "抱歉，没有找到相关的文档信息。"
        
        logger.debug(f"使用 {len(retrieved_docs)} 个文档生成回复")
        
        # 生成回复 - 使用AIHandler的chat_with_docs方法
        if use_stream:
            # 流式生成需要使用generate_response_stream方法
            logger.warning("流式生成请使用generate_response_stream方法，当前使用非流式响应代替")
        
        # 非流式生成
        return self.generation_module.chat_with_docs(query, retrieved_docs)
    
    def generate_response_stream(self, query: str, retrieved_docs: List[Document]):
        """
        流式生成回复（返回生成器）
        :param query: 查询文本
        :param retrieved_docs: 检索到的文档列表
        :return: 生成器，每次yield一个文本片段
        """
        if not self.initialized:
            self.initialize_system()
        
        if not retrieved_docs:
            logger.warning("没有检索到相关文档，将返回空回复")
            yield "抱歉，没有找到相关的文档信息。"
            return
        
        logger.debug(f"使用 {len(retrieved_docs)} 个文档流式生成回复")
        
        # 使用AIHandler的流式生成方法
        for chunk in self.generation_module.chat_with_docs_stream(query, retrieved_docs):
            yield chunk
    
    def process_query(self, query: str, filters: Optional[Dict[str, Any]] = None, 
                      top_k: int = 3, use_stream: bool = False) -> Dict[str, Any]:
        """
        处理完整的RAG查询流程
        :param query: 查询文本
        :param filters: 元数据过滤条件
        :param top_k: 返回结果数量
        :param use_stream: 是否使用流式响应（当前版本暂不支持，将使用非流式）
        :return: 包含查询结果的字典
        """
        try:
            logger.info(f"处理RAG查询: {query[:50]}...")
            
            # 1. 检索相关文档
            retrieved_docs = self.retrieve_documents(query, filters, top_k)
            
            # 2. 生成回复（流式生成需要使用process_query_stream方法）
            if use_stream:
                logger.warning("流式生成请使用process_query_stream方法，当前使用非流式响应")
            
            response = self.generate_response(query, retrieved_docs, use_stream=False)
            
            # 3. 整理结果
            result = {
                "query": query,
                "response": response,
                "retrieved_documents": [{
                    "content": doc.page_content,
                    "metadata": doc.metadata
                } for doc in retrieved_docs],
                "status": "success"
            }
            
            logger.info("RAG查询处理完成")
            return result
            
        except Exception as e:
            logger.error(f"处理RAG查询时出错: {str(e)}", exc_info=True)
            return {
                "query": query,
                "response": f"处理查询时发生错误: {str(e)}",
                "retrieved_documents": [],
                "status": "error",
                "error": str(e)
            }
    
    def process_query_stream(self, query: str, filters: Optional[Dict[str, Any]] = None, 
                            top_k: int = 3):
        """
        流式处理RAG查询流程（返回生成器）
        :param query: 查询文本
        :param filters: 元数据过滤条件
        :param top_k: 返回结果数量
        :return: 生成器，每次yield一个包含查询结果的字典片段
        """
        try:
            logger.info(f"流式处理RAG查询: {query[:50]}...")
            
            # 1. 检索相关文档
            retrieved_docs = self.retrieve_documents(query, filters, top_k)
            
            # 2. 流式生成回复
            full_response = ""
            for chunk in self.generate_response_stream(query, retrieved_docs):
                full_response += chunk
                yield {
                    "query": query,
                    "chunk": chunk,
                    "retrieved_documents": [{
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    } for doc in retrieved_docs],
                    "status": "streaming"
                }
            
            # 3. 发送完成信号
            yield {
                "query": query,
                "response": full_response,
                "retrieved_documents": [{
                    "content": doc.page_content,
                    "metadata": doc.metadata
                } for doc in retrieved_docs],
                "status": "completed"
            }
            
            logger.info("RAG流式查询处理完成")
            
        except Exception as e:
            logger.error(f"流式处理RAG查询时出错: {str(e)}", exc_info=True)
            yield {
                "query": query,
                "response": f"处理查询时发生错误: {str(e)}",
                "retrieved_documents": [],
                "status": "error",
                "error": str(e)
            }
    
    def batch_process_queries(self, queries: List[str], filters: Optional[Dict[str, Any]] = None,
                             top_k: int = 3) -> List[Dict[str, Any]]:
        """
        批量处理多个查询
        :param queries: 查询列表
        :param filters: 元数据过滤条件
        :param top_k: 返回结果数量
        :return: 结果列表
        """
        results = []
        for query in queries:
            result = self.process_query(query, filters, top_k)
            results.append(result)
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取RAG系统统计信息
        :return: 统计信息字典
        """
        stats = {
            "initialized": self.initialized,
            "documents_loaded": len(self.chunks) if self.chunks else 0,
            "retrieval_config": self.retrieval_config
        }
        
        # 如果数据处理器已初始化，获取更详细的统计
        if self.data_processor and hasattr(self.data_processor, 'get_statistics'):
            doc_stats = self.data_processor.get_statistics()
            stats.update(doc_stats)
        
        return stats
    
    def close(self):
        """
        关闭RAG系统，释放资源
        """
        logger.info("正在关闭RAG系统...")
        
        # 关闭Milvus连接
        if self.milvus_manager and hasattr(self.milvus_manager, 'close'):
            self.milvus_manager.close()
        
        self.initialized = False
        logger.info("RAG系统已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.initialize_system()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 便捷函数
def create_rag_pipeline(data_path=None, chunk_size=1000, chunk_overlap=200) -> RagModule:
    """
    创建并初始化RAG管道
    :param data_path: 数据路径（可选）
    :param chunk_size: 块大小
    :param chunk_overlap: 块重叠大小
    :return: 初始化的RAG模块
    """
    rag = RagModule()
    rag.retrieval_config.update({
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap
    })
    
    if data_path:
        from pathlib import Path
        rag.config["data_path"] = Path(data_path)
    
    rag.initialize_system()
    return rag