from typing import Optional, List, Dict, Any

from Lumina.demo.ChromaDB.DocumentManager import DocumentManager


class AdvancedChromaDBManager(DocumentManager):
    def __init__(self, collection_name: str = "documents", persist_directory: str = "./chroma_db"):
        super().__init__(collection_name, persist_directory)

    def batch_add_documents(
            self,
            documents: List[str],
            metadatas: Optional[List[Dict]] = None,
            batch_size: int = 100
    ) -> List[str]:
        """
        批量添加文档（处理大量数据）

        Args:
            documents: 文档列表
            metadatas: 元数据列表
            batch_size: 批次大小

        Returns:
            List[str]: 所有文档ID
        """
        all_ids = []

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_metadatas = None

            if metadatas:
                batch_metadatas = metadatas[i:i + batch_size]

            batch_ids = self.add_documents(batch_docs, batch_metadatas)
            all_ids.extend(batch_ids)

            print(f"已处理 {min(i + batch_size, len(documents))}/{len(documents)} 个文档")

        return all_ids

    def semantic_search(
            self,
            query: str,
            n_results: int = 5,
            score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        语义搜索（带分数过滤）

        Args:
            query: 查询文本
            n_results: 返回结果数量
            score_threshold: 相似度分数阈值

        Returns:
            List[Dict]: 搜索结果
        """
        results = self.query_documents([query], n_results=n_results)

        # 处理结果，添加分数信息
        formatted_results = []
        for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
        )):
            # 将距离转换为相似度分数（余弦相似度）
            similarity_score = 1 - distance

            if similarity_score >= score_threshold:
                formatted_results.append({
                    'document': doc,
                    'metadata': metadata,
                    'similarity_score': round(similarity_score, 4),
                    'distance': round(distance, 4),
                    'id': results['ids'][0][i]
                })

        # 按相似度排序
        formatted_results.sort(key=lambda x: x['similarity_score'], reverse=True)

        return formatted_results

    def search_with_filters(
            self,
            query: str,
            metadata_filters: Dict[str, Any],
            n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        带元数据过滤的搜索

        Args:
            query: 查询文本
            metadata_filters: 元数据过滤条件
            n_results: 返回结果数量

        Returns:
            List[Dict]: 过滤后的搜索结果
        """
        results = self.query_documents(
            [query],
            n_results=n_results,
            where=metadata_filters
        )

        formatted_results = []
        for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
        )):
            formatted_results.append({
                'document': doc,
                'metadata': metadata,
                'similarity_score': round(1 - distance, 4),
                'id': results['ids'][0][i]
            })

        return formatted_results

    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息

        Returns:
            Dict: 集合信息
        """
        count = self.count_documents()
        peek_data = self.peek_documents(limit=3)

        return {
            "collection_name": self.collection.name,
            "total_documents": count,
            "sample_documents": peek_data.get('documents', []),
            "metadata": self.collection.metadata
        }