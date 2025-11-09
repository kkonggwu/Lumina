# milvue_manager.py
import uuid
import time
from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection, utility
)
from sentence_transformers import SentenceTransformer


class ProductionReadyMilvusManager:
    def __init__(
            self,
            host: str = "localhost",
            port: str = "19530",
            collection_name: str = "documents",
            embedding_model: str = "all-MiniLM-L6-v2",
            dimension: int = 384
    ):
        """
        生产就绪的Milvus管理器
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
            print(f"✅ 成功连接到 Milvus: {self.host}:{self.port}")
        except Exception as e:
            print(f"❌ 连接Milvus失败: {e}")
            raise

    def _setup_collection(self) -> Collection:
        """创建或获取集合"""
        # 检查集合是否存在
        if utility.has_collection(self.collection_name):
            collection = Collection(self.collection_name)
            print(f"✅ 使用现有集合: {self.collection_name}")
        else:
            # 定义字段
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="document", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]

            # 创建schema
            schema = CollectionSchema(fields, description="文档存储集合")

            # 创建集合
            collection = Collection(
                name=self.collection_name,
                schema=schema,
                using='default'
            )

            # 创建索引
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }

            collection.create_index(
                field_name="vector",
                index_params=index_params
            )

            print(f"✅ 创建新集合: {self.collection_name}")

        return collection

    def _load_collection(self):
        """加载集合到内存"""
        try:
            print("🔄 正在加载集合到内存...")
            self.collection.load()

            # 等待加载完成
            retry_count = 0
            max_retries = 10
            while retry_count < max_retries:
                try:
                    # 尝试执行一个简单的查询来检查集合是否已加载
                    self.collection.query(expr="id != ''", limit=1, output_fields=["id"])
                    print("✅ 集合加载完成")
                    return
                except Exception:
                    # 如果查询失败，说明集合还在加载中
                    time.sleep(1)
                    retry_count += 1
                    print(f"等待集合加载... ({retry_count}/{max_retries})")

            print("⚠️ 集合加载可能未完成，但继续执行...")

        except Exception as e:
            print(f"❌ 加载集合失败: {e}")
            # 不要raise，继续执行，可能在搜索时自动加载

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
            metadatas: Optional[List[Dict]] = None
    ) -> List[str]:
        """
        插入文档到Milvus
        """
        if not documents:
            raise ValueError("文档列表不能为空")

        # 确保集合已加载
        if not self._is_collection_loaded():
            self._load_collection()

        # 生成嵌入向量
        embeddings = self.generate_embeddings(documents)

        # 准备数据
        ids = [str(uuid.uuid4()) for _ in range(len(documents))]

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
        insert_result = self.collection.insert(entities)

        # 刷新数据使可搜索
        self.collection.flush()

        print(f"✅ 成功插入 {len(documents)} 个文档")
        return ids

    def search_similar(
            self,
            query: str,
            limit: int = 5,
            filter_condition: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档
        """
        # 确保集合已加载
        if not self._is_collection_loaded():
            print("🔄 搜索前自动加载集合...")
            self._load_collection()

        # 生成查询向量
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
        """查询文档（基于条件过滤）"""
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
        print(f"✅ 删除 {len(ids)} 个文档")

    def drop_collection(self):
        """删除整个集合"""
        utility.drop_collection(self.collection_name)
        print(f"✅ 集合 '{self.collection_name}' 已删除")

    def close(self):
        """关闭连接"""
        try:
            # 释放集合（如果支持）
            self.collection.release()
        except:
            pass  # 忽略释放错误

        connections.disconnect("default")
        print("✅ Milvus连接已关闭")