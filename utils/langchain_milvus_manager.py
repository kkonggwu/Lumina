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
            drop_old_if_mismatch: bool = False  # 默认不删除集合，直接使用已有集合
    ):
        self.collection_name = collection_name
        self.host = host
        self.port = port

        # 使用LangChain的嵌入模型
        # 修复PyTorch设备配置问题：直接使用SentenceTransformer，然后包装为LangChain兼容格式
        try:
            import os
            # 确保使用CPU，避免GPU相关问题
            os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')
            
            logger.info(f"正在初始化嵌入模型: {embedding_model}")
            
            # 方法1: 先使用SentenceTransformer直接加载，确保模型正确初始化
            from sentence_transformers import SentenceTransformer
            
            try:
                # 直接使用SentenceTransformer加载模型
                logger.info("使用SentenceTransformer直接加载模型...")
                st_model = SentenceTransformer(embedding_model, device='cpu')
                
                # 测试模型是否正常工作
                test_embedding = st_model.encode("test", convert_to_numpy=True)
                logger.info(f"模型加载成功，测试向量维度: {len(test_embedding)}")
                
                # 创建自定义的嵌入函数，包装SentenceTransformer
                def embed_function(texts):
                    if isinstance(texts, str):
                        texts = [texts]
                    embeddings = st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
                    return embeddings.tolist() if isinstance(embeddings, list) else [embeddings.tolist()]
                
                # 使用HuggingFaceEmbeddings，但传入已加载的模型
                # 注意：HuggingFaceEmbeddings内部会尝试加载模型，我们需要避免重复加载
                # 所以直接使用自定义的嵌入函数
                from langchain_core.embeddings import Embeddings
                
                class CustomEmbeddings(Embeddings):
                    def embed_documents(self, texts):
                        return st_model.encode(texts, convert_to_numpy=True).tolist()
                    
                    def embed_query(self, text):
                        return st_model.encode([text], convert_to_numpy=True)[0].tolist()
                
                self.embeddings = CustomEmbeddings()
                logger.info("使用自定义嵌入类成功初始化")
                
            except Exception as st_e:
                logger.warning(f"使用SentenceTransformer直接加载失败: {str(st_e)}，尝试使用HuggingFaceEmbeddings...")
                # 方法2: 如果直接加载失败，使用HuggingFaceEmbeddings
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=embedding_model,
                    model_kwargs={'device': 'cpu'}
                )
                logger.info("使用HuggingFaceEmbeddings成功初始化")
            
        except Exception as e:
            logger.error(f"初始化嵌入模型失败: {str(e)}", exc_info=True)
            # 最后的备用方案：使用最简配置
            try:
                logger.warning("尝试使用最简配置初始化嵌入模型...")
                self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
                logger.info("使用最简配置成功加载嵌入模型")
            except Exception as e2:
                logger.error(f"所有初始化方法都失败: {str(e2)}", exc_info=True)
                raise RuntimeError(
                    f"无法初始化嵌入模型。错误: {str(e2)}\n"
                    f"建议：\n"
                    f"1. 检查模型文件是否完整\n"
                    f"2. 尝试删除模型缓存后重新下载\n"
                    f"3. 检查PyTorch和sentence-transformers版本是否兼容"
                )

        # 连接参数
        self.connection_args = {
            "host": host,
            "port": port
        }

        # 连接到Milvus（不删除集合，直接使用已有集合）
        self._connect_to_milvus()

        # 初始化Milvus向量存储
        # 直接使用已有集合，不删除
        # 注意：如果集合已存在但 schema 不匹配，LangChain 会报错
        # 我们会在 add_documents 方法中处理这种情况
        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
            connection_args=self.connection_args,
            drop_old=False,  # 不删除已有集合
            auto_id=True
        )

    def _connect_to_milvus(self):
        """
        连接到Milvus数据库（不删除集合，直接使用已有集合）
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
        
        # 检查集合是否存在，但不删除
        try:
            if utility.has_collection(self.collection_name):
                from pymilvus import Collection
                collection = Collection(self.collection_name)
                schema = collection.schema
                field_names = [field.name for field in schema.fields]
                logger.info(f"✅ 集合 {self.collection_name} 已存在 (字段数: {len(field_names)})，将直接使用")
            else:
                logger.info(f"集合 {self.collection_name} 不存在，LangChain将在首次插入时自动创建")
        except Exception as e:
            logger.warning(f"检查集合时出错: {str(e)}，将尝试继续初始化")

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

    def search_similar(self, query: str, limit: int = 5, filter_expr: str = None):
        """
        使用LangChain检索相似文档
        :param query: 查询文本
        :param limit: 返回结果数量
        :param filter_expr: Milvus 过滤表达式（可选），例如 'course_id == 1'
                            在向量检索时直接由 Milvus 执行过滤，效率高于 Python 层后过滤
        """
        # 构建检索参数
        search_kwargs = {"k": limit}
        if filter_expr:
            search_kwargs["expr"] = filter_expr

        # 创建标准检索器
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs
        )

        # 检索文档
        docs = retriever.get_relevant_documents(query)

        # 格式化结果
        results = []
        for doc in docs:
            results.append({
                'content': doc.page_content,
                'metadata': doc.metadata,
                'score': getattr(doc, 'score', 0.0)
            })

        return results

    def get_retriever(self, **kwargs):
        """获取LangChain标准检索器"""
        return self.vector_store.as_retriever(**kwargs)
    
    def _get_default_value_for_field(self, field):
        """
        根据字段类型返回合适的默认值
        
        :param field: Milvus FieldSchema 对象
        :return: 默认值
        """
        from pymilvus import DataType
        
        # 根据字段类型返回默认值
        if field.dtype == DataType.VARCHAR:
            return ""  # 字符串类型返回空字符串
        elif field.dtype == DataType.INT8 or field.dtype == DataType.INT16 or \
             field.dtype == DataType.INT32 or field.dtype == DataType.INT64:
            return 0  # 整数类型返回0
        elif field.dtype == DataType.FLOAT or field.dtype == DataType.DOUBLE:
            return 0.0  # 浮点数类型返回0.0
        elif field.dtype == DataType.BOOL:
            return False  # 布尔类型返回False
        elif field.dtype == DataType.JSON:
            return {}  # JSON类型返回空字典
        else:
            # 其他类型默认返回空字符串
            return ""
    
    def add_documents(self, documents: List[Document]):
        """
        添加文档到向量存储（兼容LangChain接口）
        处理 schema 不匹配问题：如果集合已存在，确保新文档的 metadata 包含所有必需字段
        
        :param documents: Document对象列表
        :return: 文档ID列表
        """
        if not documents:
            return []
        
        # 检查集合是否存在，如果存在，获取其 schema 并填充缺失的 metadata 字段
        try:
            if utility.has_collection(self.collection_name):
                from pymilvus import Collection
                collection = Collection(self.collection_name)
                schema = collection.schema
                
                # LangChain Milvus 的系统字段通常是：id, vector, text (或 page_content)
                # 其他字段都是 metadata 字段
                system_fields = {'id', 'vector', 'text', 'page_content'}
                
                # 创建字段名到字段对象的映射，以便获取字段类型
                field_map = {
                    field.name: field 
                    for field in schema.fields 
                    if field.name not in system_fields
                }
                existing_metadata_fields = set(field_map.keys())
                
                # 如果集合有 metadata 字段，需要确保新文档包含这些字段
                if existing_metadata_fields:
                    logger.info(
                        f"集合已有 {len(existing_metadata_fields)} 个 metadata 字段: "
                        f"{list(existing_metadata_fields)[:10]}..."  # 只显示前10个
                    )
                    
                    # 获取第一个文档的所有 metadata 键
                    if documents and documents[0].metadata:
                        first_doc_metadata_keys = set(documents[0].metadata.keys())
                        missing_fields = existing_metadata_fields - first_doc_metadata_keys
                        
                        if missing_fields:
                            logger.warning(
                                f"检测到缺失的 metadata 字段 ({len(missing_fields)} 个): "
                                f"{list(missing_fields)[:10]}...，"
                                f"将根据字段类型填充合适的默认值"
                            )
                            
                            # 为所有文档填充缺失的字段，根据字段类型使用合适的默认值
                            for doc in documents:
                                for field_name in missing_fields:
                                    if field_name not in doc.metadata:
                                        field = field_map[field_name]
                                        default_value = self._get_default_value_for_field(field)
                                        doc.metadata[field_name] = default_value
                                        logger.debug(
                                            f"为字段 {field_name} (类型: {field.dtype}) "
                                            f"填充默认值: {default_value}"
                                        )
        except Exception as e:
            logger.warning(f"检查集合 schema 时出错: {str(e)}，将尝试直接插入")
        
        # 使用LangChain添加文档（自动处理向量化）
        try:
            doc_ids = self.vector_store.add_documents(documents)
            logger.info(f"成功添加 {len(documents)} 个文档到 Milvus")
            return doc_ids
        except Exception as e:
            error_msg = str(e)
            # 如果是 schema 不匹配错误，提供更详细的错误信息和解决方案
            if "doesn't match with schema" in error_msg or "DataNotMatchException" in error_msg or "ParamError" in error_msg:
                logger.error(
                    f"Schema 不匹配错误: {error_msg}\n"
                    f"原因：集合的 schema 期望的字段类型或数量与新文档不匹配。\n"
                    f"解决方案：\n"
                    f"  1. 删除现有集合（会丢失所有数据）：\n"
                    f"     在 Milvus 中执行: drop collection {self.collection_name}\n"
                    f"  2. 或者确保新文档的 metadata 包含集合中所有已有的字段，且类型匹配。"
                )
                # 尝试获取集合的详细信息以便调试
                try:
                    if utility.has_collection(self.collection_name):
                        from pymilvus import Collection
                        collection = Collection(self.collection_name)
                        schema = collection.schema
                        field_info = [
                            f"{field.name}({field.dtype})" 
                            for field in schema.fields
                        ]
                        logger.error(f"集合字段详情: {field_info}")
                except:
                    pass
            raise