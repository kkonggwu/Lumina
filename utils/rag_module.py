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

        # 检查API密钥
        if not DASHSCOPE_API_KEY:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量")

    def initialize_system(self, load_static_documents=False):
        """
        初始化所有模块
        
        Args:
            load_static_documents: 是否加载静态文档（已废弃，不再加载静态文档）
        """
        logger.info("开始初始化RAG系统...")
        
        # 初始化Milvus管理器（不加载静态文档）
        self.milvus_manager = LangChainMilvusManager()
        logger.info("Milvus管理器初始化完成")
        
        # 初始化AI处理器
        self.generation_module = AIHandler(
            api_key=self.api_key,
            api_base=self.config["api_base"]
        )
        logger.info("AI处理器初始化完成")
        
        # 初始化检索优化模块（使用已有的向量存储）
        if self.milvus_manager.vector_store:
            self.retrieval_module = RetrievalOptimization(
                vectorstore=self.milvus_manager.vector_store,
                chunks=[]  # 不再预加载chunks，文档通过上传接口动态添加
            )
            logger.info("检索优化模块初始化完成")
        
        self.initialized = True
        logger.info("RAG系统初始化完成（不加载静态文档）")
    
    def load_and_process_documents(self) -> List[Document]:
        """
        加载并处理文档（已废弃，不再加载静态文档）
        文档现在通过上传接口动态添加到Milvus
        
        :return: 空列表（不再加载静态文档）
        """
        logger.warning("load_and_process_documents 方法已废弃，不再加载静态文档")
        logger.info("文档现在通过上传接口动态添加到Milvus数据库")
        return []
    
    def index_documents(self, chunks: Optional[List[Document]] = None):
        """
        将文档块索引到向量数据库（已废弃，文档现在通过上传接口直接索引）
        :param chunks: 文档块列表（已废弃）
        """
        logger.warning("index_documents 方法已废弃，文档现在通过上传接口直接索引到Milvus")
        logger.info("请使用 DocumentService.upload_document 方法上传文档")
        # 如果提供了chunks，仍然可以索引（用于兼容性）
        if chunks:
            if not self.initialized:
                self.initialize_system()
            logger.info(f"索引 {len(chunks)} 个文档块到Milvus...")
            self.milvus_manager.add_documents(chunks)
            logger.info("文档索引完成")
    
    def retrieve_documents(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None, 
        top_k: int = 3,
        similarity_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        根据查询检索相关文档
        :param query: 查询文本
        :param filters: 元数据过滤条件
        :param top_k: 返回结果数量
        :param similarity_threshold: 相似度阈值，低于此值的文档将被过滤（0-1之间，None表示不过滤）
        :return: 检索到的文档列表
        """
        if not self.retrieval_module:
            raise ValueError("检索模块未初始化，请先调用initialize_system方法")
        
        logger.info(f"开始检索文档，查询: {query[:50]}...")
        
        if filters:
            # 使用带元数据过滤的检索
            docs = self.retrieval_module.metadata_filtered_search(query, filters, top_k, similarity_threshold)
        else:
            # 使用混合检索
            docs = self.retrieval_module.hybrid_search(query, top_k, similarity_threshold)
        
        logger.info(f"检索完成，找到 {len(docs)} 个相关文档")
        return docs
    
    async def check_document_relevance(self, query: str, retrieved_docs: List[Document]) -> bool:
        """
        使用AI判断检索到的文档是否与用户问题相关
        
        :param query: 用户问题
        :param retrieved_docs: 检索到的文档列表
        :return: True表示相关，False表示不相关
        """
        if not retrieved_docs:
            return False
        
        try:
            # 构建上下文
            context = self.generation_module._build_context(retrieved_docs, max_length=1000)
            
            # 使用AI判断相关性
            from utils.prompt_template import DOCUMENT_RELEVANCE_CHECK_PROMPT
            prompt = DOCUMENT_RELEVANCE_CHECK_PROMPT.format(query=query, context=context)
            
            # 调用AI进行判断（get_completion是异步方法）
            result = await self.generation_module.get_completion(prompt, max_tokens=50, temperature=0.1)
            
            # 解析结果
            result_lower = result.strip().lower()
            # 如果包含"不相关"，则判断为不相关；否则判断为相关
            is_relevant = "不相关" not in result_lower and ("相关" in result_lower or len(result_lower) > 0)
            
            logger.info(f"AI判断文档相关性: {is_relevant} (AI回答: {result.strip()})")
            return is_relevant
            
        except Exception as e:
            logger.error(f"AI判断文档相关性时出错: {str(e)}", exc_info=True)
            # 出错时默认认为相关，避免误过滤
            return True
    
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
            return "抱歉，没有搜寻到与您的问题相关的文档信息。"
        
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
            yield "抱歉，没有搜寻到与您的问题相关的文档信息。"
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
    
    def process_query_stream(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None, 
        top_k: int = 3,
        similarity_threshold: Optional[float] = 0.3
    ):
        """
        流式处理RAG查询流程（返回生成器）
        :param query: 查询文本
        :param filters: 元数据过滤条件
        :param top_k: 返回结果数量
        :param similarity_threshold: 相似度阈值，低于此值的文档将被过滤（0-1之间，None表示不过滤，默认0.3）
        :return: 生成器，每次yield一个包含查询结果的字典片段
        """
        try:
            logger.info(f"流式处理RAG查询: {query[:50]}...")
            
            # 1. 检索相关文档（应用相似度阈值过滤）
            retrieved_docs = self.retrieve_documents(query, filters, top_k, similarity_threshold)
            
            # 2. 如果过滤后没有文档，返回提示信息
            if not retrieved_docs:
                logger.warning("相似度过滤后没有相关文档，返回无相关文档提示")
                no_relevant_docs_response = "抱歉，没有搜寻到与您的问题相关的文档信息。"
                yield {
                    "query": query,
                    "chunk": no_relevant_docs_response,
                    "retrieved_documents": [],
                    "status": "streaming"
                }
                yield {
                    "query": query,
                    "response": no_relevant_docs_response,
                    "retrieved_documents": [],
                    "status": "completed"
                }
                return
            
            # 3. 流式生成回复
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
            
            # 4. 发送完成信号
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
def create_rag_pipeline(data_path=None, chunk_size=1000, chunk_overlap=200, initialize_with_documents=True) -> RagModule:
    """
    创建并初始化RAG管道
    
    :param data_path: 数据路径（可选，已废弃，不再加载静态文档）
    :param chunk_size: 块大小
    :param chunk_overlap: 块重叠大小
    :param initialize_with_documents: 是否初始化时加载文档（已废弃，始终为False）
    :return: 初始化的RAG模块
    """
    rag = RagModule()
    rag.retrieval_config.update({
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap
    })
    
    # 不再使用data_path加载静态文档
    # 文档现在通过上传接口动态添加到Milvus
    
    # 初始化系统（不加载静态文档）
    rag.initialize_system(load_static_documents=False)
    return rag