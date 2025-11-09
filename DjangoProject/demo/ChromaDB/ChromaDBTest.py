import os
import subprocess
import sys
from sentence_transformers import SentenceTransformer
import chromadb
import uuid
from typing import List, Dict, Any, Optional


def setup_environment():
    """设置环境，禁用警告"""
    # 禁用符号链接警告
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

    # 设置缓存路径
    cache_dir = "models/cache"
    os.makedirs(cache_dir, exist_ok=True)
    os.environ['TRANSFORMERS_CACHE'] = cache_dir
    os.environ['HF_HOME'] = cache_dir

    print("环境设置完成")


def download_model_with_mirror(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """
    使用镜像源下载模型

    Args:
        model_name: 模型名称
    """
    print(f"开始下载模型: {model_name}")

    # 设置镜像源
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

    # 创建模型目录
    local_dir = f"models/{model_name.split('/')[-1]}"
    os.makedirs(local_dir, exist_ok=True)

    # 下载命令
    cmd = [
        'huggingface-cli', 'download',
        model_name,
        '--local-dir', local_dir,
        '--resume-download'
    ]

    try:
        print("正在下载模型，这可能需要几分钟...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 模型下载完成！")
        print(f"模型保存在: {local_dir}")
        return local_dir
    except subprocess.CalledProcessError as e:
        print(f"❌ 下载失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ 请先安装 huggingface_hub: pip install huggingface_hub")
        return None


def check_model_downloaded(model_name: str = "all-MiniLM-L6-v2"):
    """检查模型是否已下载"""
    model_path = f"models/{model_name}"
    if os.path.exists(model_path):
        print(f"✅ 模型已存在: {model_path}")
        return model_path
    else:
        print(f"❌ 模型未找到: {model_path}")
        return None


class ChromaDBWithLocalModel:
    def __init__(self, model_path: str = None, persist_directory: str = "./chroma_db"):
        """
        使用本地模型的ChromaDB管理器
        """
        setup_environment()

        # 检查模型路径
        if model_path is None:
            model_path = check_model_downloaded()
            if model_path is None:
                print("请先下载模型")
                return

        # 加载本地模型
        print("正在加载模型...")
        try:
            self.embedding_model = SentenceTransformer(model_path)
            print("✅ 模型加载成功")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return

        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)
        print(f"✅ ChromaDB初始化完成，数据存储在: {persist_directory}")

    def create_collection(self, collection_name: str = "documents"):
        """创建集合"""
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"✅ 集合 '{collection_name}' 创建成功")
        return self.collection

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入向量"""
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()

    def add_documents(self, documents: List[str], metadatas: Optional[List[Dict]] = None):
        """添加文档到集合"""
        if not documents:
            raise ValueError("文档列表不能为空")

        # 生成嵌入向量
        embeddings = self.generate_embeddings(documents)

        # 自动生成ID
        ids = [str(uuid.uuid4()) for _ in range(len(documents))]

        # 处理元数据
        if metadatas is None:
            metadatas = [{} for _ in documents]
        elif len(metadatas) != len(documents):
            metadatas = [{} for _ in documents]

        # 添加到集合
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ 成功添加 {len(documents)} 个文档")
        return ids

    def search_documents(self, query: str, n_results: int = 3):
        """搜索相似文档"""
        # 生成查询嵌入
        query_embedding = self.generate_embeddings([query])[0]

        # 搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        return results

    def get_collection_info(self):
        """获取集合信息"""
        count = self.collection.count()
        return {
            "collection_name": self.collection.name,
            "total_documents": count,
            "metadata": self.collection.metadata
        }


def demo_chromadb_functionality():
    """
    演示完整的ChromaDB功能：下载模型 + 测试使用
    """
    print("=" * 60)
    print("ChromaDB 功能演示")
    print("=" * 60)

    # 步骤1：下载模型
    print("\n📥 步骤1: 下载模型")
    model_path = download_model_with_mirror()

    if model_path is None:
        # 如果下载失败，尝试检查是否已存在
        model_path = check_model_downloaded()
        if model_path is None:
            print("❌ 无法获取模型，退出演示")
            return

    # 步骤2：初始化ChromaDB
    print("\n🔄 步骤2: 初始化ChromaDB")
    try:
        chroma_manager = ChromaDBWithLocalModel(model_path)
        chroma_manager.create_collection("demo_documents")
    except Exception as e:
        print(f"❌ ChromaDB初始化失败: {e}")
        return

    # 步骤3：添加测试数据
    print("\n📝 步骤3: 添加测试文档")
    documents = [
        "机器学习是人工智能的一个重要分支，专注于从数据中学习模式",
        "深度学习使用多层神经网络进行自动特征学习和复杂模式识别",
        "自然语言处理（NLP）使计算机能够理解、解释和生成人类语言",
        "计算机视觉致力于让计算机从图像和视频中获取高级理解",
        "强化学习通过试错和奖励机制学习最优决策策略",
        "Transformer模型在自然语言处理领域取得了革命性突破",
        "BERT模型通过双向编码器实现深度语言理解",
        "GPT模型能够生成流畅、连贯的文本内容"
    ]

    metadatas = [
        {"category": "AI基础", "source": "教材", "difficulty": "初级"},
        {"category": "深度学习", "source": "论文", "difficulty": "高级"},
        {"category": "NLP", "source": "博客", "difficulty": "中级"},
        {"category": "CV", "source": "教程", "difficulty": "中级"},
        {"category": "强化学习", "source": "教材", "difficulty": "高级"},
        {"category": "NLP", "source": "论文", "difficulty": "高级"},
        {"category": "NLP", "source": "论文", "difficulty": "高级"},
        {"category": "NLP", "source": "论文", "difficulty": "高级"}
    ]

    try:
        ids = chroma_manager.add_documents(documents, metadatas)
        print(f"✅ 成功添加 {len(ids)} 个测试文档")
    except Exception as e:
        print(f"❌ 添加文档失败: {e}")
        return

    # 步骤4：测试搜索功能
    print("\n🔍 步骤4: 测试搜索功能")

    test_queries = [
        "什么是机器学习？",
        "自然语言处理有哪些应用？",
        "深度学习的特点是什么？"
    ]

    for query in test_queries:
        print(f"\n搜索查询: '{query}'")
        print("-" * 40)

        try:
            results = chroma_manager.search_documents(query, n_results=2)

            for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
            )):
                similarity = 1 - distance
                print(f"{i + 1}. 相似度: {similarity:.4f}")
                print(f"   文档: {doc[:80]}...")
                print(f"   元数据: {metadata}")
                print()

        except Exception as e:
            print(f"❌ 搜索失败: {e}")

    # 步骤5：显示集合信息
    print("\n📊 步骤5: 集合信息")
    try:
        info = chroma_manager.get_collection_info()
        print(f"集合名称: {info['collection_name']}")
        print(f"文档总数: {info['total_documents']}")
        print(f"集合元数据: {info['metadata']}")
    except Exception as e:
        print(f"❌ 获取集合信息失败: {e}")

    print("\n" + "=" * 60)
    print("🎉 ChromaDB 功能演示完成！")
    print("=" * 60)


def check_dependencies():
    """检查依赖是否安装"""
    required_packages = ['chromadb', 'sentence-transformers', 'huggingface_hub']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ 缺少必要的依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装:")
        print("pip install chromadb sentence-transformers huggingface_hub")
        return False

    print("✅ 所有依赖包已安装")
    return True


if __name__ == "__main__":
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 运行演示
    demo_chromadb_functionality()