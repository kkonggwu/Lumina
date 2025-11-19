#!/usr/bin/env python3
from pymilvus import connections, Collection, utility


def diagnose_collection(collection_name):
    print("=== Milvus 集合诊断 ===")

    # 连接
    connections.connect(alias="default", host="localhost", port="19530")

    # 检查集合是否存在
    if not utility.has_collection(collection_name):
        print(f"集合 '{collection_name}' 不存在")
        return

    collection = Collection(collection_name)
    collection.flush()
    # 检查加载状态
    try:
        collection.load()
        print("✓ 集合加载成功")
    except Exception as e:
        print(f"✗ 集合加载失败: {e}")
        return

    # 多种方式检查数据量
    print("\n--- 数据量检查 ---")

    # 方法1: num_entities
    num_entities = collection.num_entities
    print(f"num_entities: {num_entities}")

    # 方法2: 查询计数
    results = collection.query(expr="", output_fields=["*"], limit=1000)
    print(f"query 返回记录数: {len(results)}")

    # 方法3: 统计信息
    try:
        stats = utility.get_collection_stats(collection_name)
        print(f"集合统计: {stats}")
    except Exception as e:
        print(f"获取统计信息失败: {e}")

    # 检查实际数据
    print(f"\n--- 实际数据样本 (前3条) ---")
    if len(results) > 0:
        for i, item in enumerate(results[:3]):
            print(f"记录 {i + 1}:")
            for key, value in list(item.items())[:5]:  # 只显示前5个字段
                print(f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
            if len(item) > 5:
                print(f"  ... 还有 {len(item) - 5} 个字段")
            print()
    else:
        print("没有查询到数据")

    # 检查字段结构
    print(f"\n--- 集合结构 ---")
    schema = collection.schema
    for field in schema.fields:
        print(f"字段: {field.name}, 类型: {field.dtype}, 主键: {field.is_primary}")


# 执行诊断
diagnose_collection('documents')