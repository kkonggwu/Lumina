import time
import uuid
from typing import List, Dict, Any, Optional

from utils.logger import get_logger

# 使用LoggerManager
logger = get_logger('milvus_manager')
from pymilvus import (
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection, utility
)
from sentence_transformers import SentenceTransformer

class MilvusManager:
    def __init__(
            self,
            host: str = "localhost",
            port: str = "19530",
            collection_name: str = "documents",
            embedding_model: str = "all-MiniLM-L6-v2",
            dimension: int = 384
    ):
        """
        :param host:
        :param port:
        :param collection_name: 数据库表名（根据不同知识库进行区分）
        :param embedding_model: 嵌入模型
        :param dimension: 嵌入维度
        """

        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.dimension = dimension

        # 连接Milvus
        self._connect()

        # 加载嵌入模型
        self.embedding_model = SentenceTransformer(embedding_model)

        # 初始化集合
        self.collection = self._setup_collection()

        # 加载集合到内存
        self._load_collection()

    def _connect(self):
        """连接Milvus数据库"""
        try:
            connections.connect(
                "default",
                host=self.host,
                port=self.port
            )
            logger.info(f"Connected to {self.host}:{self.port} successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")

    def _setup_collection(self, description: str ="文档存储集合") -> Collection:
        """创建或获取集合"""
        if utility.has_collection(self.collection_name):
            # 使用现有的 collection
            collection = Collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} already exists.")
        else:
            # 创建新的 collection
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="document", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]

            # 创建 schema
            schema = CollectionSchema(fields=fields, description=description)

            # 创建 collection
            collection = Collection(
                name=self.collection_name,
                schema=schema,
                using='default'
            )

            # 创建索引
            index_params = {
                "metric_type": "L2", # L2(欧几里得距离)
                "index_type": "IVF_FLAT", #
                "params": {"nlist": 128} # 将整个向量空间划分为128个聚类单元
            }

            collection.create_index(
                field_name="vector",
                index_params=index_params
            )

            logger.info(f"✅ Created collection {self.collection_name} successfully.")

        return collection

    def _load_collection(self):
        """加载集合到内存"""
        try:
            logger.info("🔄 正在加载集合到内存...")
            self.collection.load()

            # 等待加载完成
            retry_count = 0
            max_retries = 10
            while retry_count < max_retries:
                try:
                    # 尝试执行一个简单的查询来检查集合是否已加载
                    self.collection.query(expr="id != ''", limit=1, output_fields=["id"])
                    logger.info("✅ 集合加载完成")
                    return
                except Exception:
                    # 如果查询失败，说明集合还在加载中
                    time.sleep(1)
                    retry_count += 1
                    logger.info(f"等待集合加载... ({retry_count}/{max_retries})")

            logger.warning("⚠️ 集合加载可能未完成，但继续执行...")

        except Exception as e:
            logger.error(f"❌ 加载集合失败: {e}")


    def _is_collection_loaded(self) -> bool:
        """检查集合是否已加载"""
        try:
            # 尝试执行一个简单的查询来检查集合状态
            self.collection.query(expr="id != ''", limit=1, output_fields=["id"])
            return True
        except Exception:
            return False


    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入向量"""
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()


    def insert_documents(
            self,
            documents: List[str],
            metadatas: List[str]
    ) -> List[str]:
        """
        插入文档到 Milvus
        :param documents: 文档列表
        :param metadatas: 文档元信息
        :return: 返回文档 id
        """
        if not documents:
            raise ValueError("文档不能列表为空")

        # collection 加载之后才继续运行
        if not self._is_collection_loaded():
            self._load_collection()

        # 生成嵌入向量
        embeddings = self.generate_embeddings(documents)

        # 准备数据
        ids = [str(uuid.uuid4()) for _ in range(len(documents))]
        # 元数据为空则设置默认值
        if metadatas is None:
            metadatas = [{} for _ in documents]

        # 准备插入数据
        entities = [
            ids,  # id字段
            documents,  # document字段
            embeddings,  # vector字段
            metadatas  # metadata字段
        ]

        # 插入数据
        result = self.collection.insert(entities)
        # 刷新数据，确保可以被检索到
        self.collection.flush()
        logger.info(f"✅ 成功插入 {len(documents)} 个文档")
        return ids

    def search_similar(
            self,
            query: str,
            limit: int = 5,
            filter_condition: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档
        :param query: 查询语句
        :param limit: 查询文档数
        :param filter_condition:
        :return:
        """
        # 确保集合已加载
        if not self._is_collection_loaded():
            logger.info("🔄 搜索前自动加载集合...")
            self._load_collection()

        query_embedding = self.generate_embeddings([query])[0]
        # 定义搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }

        # 执行搜索
        results = self.collection.search(
            data=[query_embedding],
            anns_field="vector",
            param=search_params,
            limit=limit,
            expr=filter_condition,
            output_fields=["document", "metadata", "id"]
        )

        # 格式化结果
        formatted_results = []
        for hits in results:
            for hit in hits:
                formatted_results.append({
                    'id': hit.id,
                    'document': hit.entity.get('document'),
                    'metadata': hit.entity.get('metadata'),
                    'distance': hit.distance,
                    'score': 1 - hit.distance  # 相似度分数
                })

        return formatted_results


    def query_documents(
            self,
            filter_condition: str,
            limit: int = 10,
            output_fields: List[str] = None
    ):
        """
        查询文档（基于元信息过滤）
        :param filter_condition: 过滤条件
        :param limit: 查询个数
        :param output_fields:
        :return:
        """
        if output_fields is None:
            output_fields = ["id", "document", "metadata"]

        results = self.collection.query(
            expr=filter_condition,
            limit=limit,
            output_fields=output_fields
        )

        return results

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        stats = self.collection.num_entities
        return {
            'collection_name': self.collection_name,
            'total_documents': stats,
            'is_loaded': self._is_collection_loaded()
        }

    def delete_documents(self, ids: List[str]):
        """删除文档"""
        # 构建删除表达式
        id_list = ', '.join([f"'{id}'" for id in ids])
        expr = f"id in [{id_list}]"

        self.collection.delete(expr)
        self.collection.flush()
        logger.info(f"✅ 删除 {len(ids)} 个文档")

    def drop_collection(self):
        """删除整个集合"""
        utility.drop_collection(self.collection_name)
        logger.info(f"✅ 集合 '{self.collection_name}' 已删除")

    def close(self):
        """关闭连接"""
        try:
            # 释放集合（如果支持）
            self.collection.release()
        except:
            pass  # 忽略释放错误

        connections.disconnect("default")
        logger.info("✅ Milvus连接已关闭")










