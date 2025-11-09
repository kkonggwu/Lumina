# demo.py
from milvus_manager import ProductionReadyMilvusManager
import time


def demo_production_milvus():
    """演示生产就绪的Milvus使用"""

    print("🚀 启动Milvus演示...")

    try:
        # 初始化管理器
        manager = ProductionReadyMilvusManager()

        # 显示集合状态
        stats = manager.get_collection_stats()
        print(f"📊 初始状态: {stats}")

        # 添加测试数据
        documents = [
            "机器学习是人工智能的一个重要分支，让计算机从数据中学习",
            "深度学习使用神经网络模型处理复杂模式识别任务",
            "自然语言处理(NLP)专注于计算机与人类语言的交互",
            "计算机视觉让计算机能够理解和分析图像内容"
        ]

        metadatas = [
            {"category": "AI基础", "source": "教材", "timestamp": "2024-01-01"},
            {"category": "深度学习", "source": "论文", "timestamp": "2024-01-02"},
            {"category": "NLP", "source": "博客", "timestamp": "2024-01-03"},
            {"category": "CV", "source": "教程", "timestamp": "2024-01-04"}
        ]

        print("📝 添加示例文档...")
        doc_ids = manager.insert_documents(documents, metadatas)
        print(f"📄 插入的文档ID: {doc_ids}")

        # 等待一下确保数据刷新
        time.sleep(2)

        # 显示插入后的状态
        stats = manager.get_collection_stats()
        print(f"📊 插入后状态: {stats}")

        # 测试搜索功能
        print("🔍 测试搜索功能...")

        test_queries = [
            "什么是机器学习？",
            "自然语言处理有哪些应用？",
            "深度学习的特点是什么？"
        ]

        for query in test_queries:
            print(f"\n搜索查询: '{query}'")
            print("-" * 50)

            try:
                results = manager.search_similar(query, limit=2)

                if not results:
                    print("❌ 没有找到相关结果")
                    continue

                for i, result in enumerate(results):
                    print(f"{i + 1}. 相似度: {result['score']:.4f} (距离: {result['distance']:.4f})")
                    print(f"   文档: {result['document']}")
                    print(f"   元数据: {result['metadata']}")
                    print(f"   ID: {result['id']}")
                    print()

            except Exception as e:
                print(f"❌ 搜索失败: {e}")
                # 继续测试下一个查询

        # 测试查询功能（基于元数据过滤）
        print("\n🔍 测试查询功能（基于元数据过滤）...")
        try:
            query_results = manager.query_documents(
                filter_condition='metadata["category"] == "AI基础"',
                limit=2
            )

            print("查询条件: category == 'AI基础'")
            for i, result in enumerate(query_results):
                print(f"{i + 1}. ID: {result['id']}")
                print(f"   文档: {result['document']}")
                print(f"   元数据: {result['metadata']}")
                print()

        except Exception as e:
            print(f"查询失败: {e}")

        # 最终统计信息
        final_stats = manager.get_collection_stats()
        print(f"\n📊 最终统计:")
        print(f"   集合名称: {final_stats['collection_name']}")
        print(f"   文档总数: {final_stats['total_documents']}")
        print(f"   是否加载: {final_stats['is_loaded']}")

    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")

    finally:
        # 确保连接被关闭
        try:
            manager.close()
        except:
            pass

    print("\n🎉 Milvus演示完成！")


def cleanup_and_restart():
    """清理并重新开始"""
    print("🧹 清理环境...")

    try:
        from pymilvus import connections, utility

        connections.connect("default", host="localhost", port="19530")

        # 删除现有集合
        if utility.has_collection("documents"):
            utility.drop_collection("documents")
            print("✅ 已删除现有集合")

        connections.disconnect("default")

    except Exception as e:
        print(f"清理失败: {e}")


if __name__ == "__main__":
    # 如果需要重新开始，取消下面的注释
    # cleanup_and_restart()

    demo_production_milvus()