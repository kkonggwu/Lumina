from typing import Optional, Dict, List

import chromadb
from sentence_transformers import SentenceTransformer


class ChromaDBManager:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        初始化ChromaDB管理器

        Args:
            persist_directory: 数据持久化目录路径
        """
        # 创建持久化客户端
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        print(f"ChromaDB初始化完成，数据存储在: {persist_directory}")

    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None) -> chromadb.Collection:
        """
        创建或获取集合

        Args:
            collection_name: 集合名称
            metadata: 集合元数据

        Returns:
            chromadb.Collection: 集合对象
        """
        if metadata is None:
            metadata = {"description": "Default collection"}

        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata=metadata
            )
            print(f"集合 '{collection_name}' 创建/获取成功")
            return collection
        except Exception as e:
            print(f"创建集合失败: {e}")
            raise

    def delete_collection(self, collection_name: str) -> bool:
        """
        删除集合

        Args:
            collection_name: 集合名称

        Returns:
            bool: 是否删除成功
        """
        try:
            self.client.delete_collection(collection_name)
            print(f"集合 '{collection_name}' 删除成功")
            return True
        except Exception as e:
            print(f"删除集合失败: {e}")
            return False

    def list_collections(self) -> List[str]:
        """
        列出所有集合

        Returns:
            List[str]: 集合名称列表
        """
        collections = self.client.list_collections()
        collection_names = [col.name for col in collections]
        print(f"现有集合: {collection_names}")
        return collection_names
