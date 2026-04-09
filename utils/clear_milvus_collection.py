#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速清理Milvus集合的工具脚本
用于删除documents集合，让LangChain重新创建
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lumina.settings')

import django
django.setup()

from pymilvus import connections, utility, Collection

def clear_collection(collection_name="documents"):
    """删除指定的集合"""
    try:
        print(f"🔗 连接到Milvus...")
        connections.connect(
            "default",
            host="localhost",
            port="19530"
        )
        
        if not utility.has_collection(collection_name):
            print(f"✅ 集合 '{collection_name}' 不存在，无需删除")
            return True
        
        # 获取集合信息
        collection = Collection(collection_name)
        try:
            num_entities = collection.num_entities
            print(f"📊 集合中有 {num_entities} 条数据")
        except:
            pass
        
        schema = collection.schema
        field_names = [field.name for field in schema.fields]
        print(f"📋 集合字段数: {len(field_names)}")
        print(f"   字段列表: {field_names[:10]}{'...' if len(field_names) > 10 else ''}")
        
        print(f"\n🗑️  正在删除集合 '{collection_name}'...")
        utility.drop_collection(collection_name)
        
        print(f"✅ 成功删除集合 '{collection_name}'")
        print(f"\n💡 提示: 现在可以重新运行测试，LangChain会自动创建新集合")
        return True
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='清理Milvus集合')
    parser.add_argument(
        '--collection',
        type=str,
        default='documents',
        help='集合名称（默认: documents）'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Milvus集合清理工具")
    print("=" * 60)
    print()
    
    clear_collection(args.collection)




