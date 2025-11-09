import uuid
from typing import List, Optional, Dict, Any

from DjangoProject.demo.ChromaDB.ChromaDB import ChromaDBManager


class DocumentManager(ChromaDBManager):
    def __init__(self, collection_name: str = "documents", persist_directory: str = "./chroma_db"):
        """
        文档管理器

        Args:
            collection_name: 默认集合名称
            persist_directory: 数据持久化目录
        """
        super().__init__(persist_directory)
        self.collection = self.create_collection(collection_name)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本嵌入向量

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 嵌入向量列表
        """
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()

    def add_documents(
            self,
            documents: List[str],
            metadatas: Optional[List[Dict]] = None,
            ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档到集合

        Args:
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: 文档ID列表

        Returns:
            List[str]: 添加的文档ID列表
        """
        if not documents:
            raise ValueError("文档列表不能为空")

        # 生成嵌入向量
        embeddings = self.generate_embeddings(documents)

        # 自动生成ID
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

        # 处理元数据
        if metadatas is None:
            metadatas = [{} for _ in documents]
        elif len(metadatas) != len(documents):
            raise ValueError("元数据列表长度必须与文档列表长度一致")

        # 添加文档到集合
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"成功添加 {len(documents)} 个文档")
        return ids

    def query_documents(
            self,
            query_texts: List[str],
            n_results: int = 5,
            where: Optional[Dict] = None,
            where_document: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        查询相似文档

        Args:
            query_texts: 查询文本列表
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件

        Returns:
            Dict: 查询结果
        """
        # 生成查询嵌入向量
        query_embeddings = self.generate_embeddings(query_texts)

        # 执行查询
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            where_document=where_document
        )

        return results

    def get_documents(
            self,
            ids: Optional[List[str]] = None,
            where: Optional[Dict] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取文档

        Args:
            ids: 文档ID列表
            where: 过滤条件
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            Dict: 文档结果
        """
        return self.collection.get(
            ids=ids,
            where=where,
            limit=limit,
            offset=offset
        )

    def update_documents(
            self,
            ids: List[str],
            documents: Optional[List[str]] = None,
            metadatas: Optional[List[Dict]] = None
    ) -> bool:
        """
        更新文档

        Args:
            ids: 文档ID列表
            documents: 新的文档内容
            metadatas: 新的元数据

        Returns:
            bool: 是否更新成功
        """
        try:
            update_data = {"ids": ids}

            if documents is not None:
                update_data["documents"] = documents
                # 重新生成嵌入向量
                update_data["embeddings"] = self.generate_embeddings(documents)

            if metadatas is not None:
                update_data["metadatas"] = metadatas

            self.collection.update(**update_data)
            print(f"成功更新 {len(ids)} 个文档")
            return True
        except Exception as e:
            print(f"更新文档失败: {e}")
            return False

    def delete_documents(self, ids: List[str]) -> bool:
        """
        删除文档

        Args:
            ids: 要删除的文档ID列表

        Returns:
            bool: 是否删除成功
        """
        try:
            self.collection.delete(ids=ids)
            print(f"成功删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            print(f"删除文档失败: {e}")
            return False

    def count_documents(self) -> int:
        """
        统计集合中的文档数量

        Returns:
            int: 文档数量
        """
        return self.collection.count()

    def peek_documents(self, limit: int = 5) -> Dict[str, Any]:
        """
        预览文档

        Args:
            limit: 预览数量

        Returns:
            Dict: 预览结果
        """
        return self.collection.peek(limit=limit)