#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RetrieverAgent 检索功能测试

用法:
    python Test/retriever_agent_test.py

测试内容:
1. enable_milvus=False 时, 通过 Mock 数据调用 retrieve(), 验证返回结构是否正常
   (跳过真实数据库依赖, 只验证逻辑与字段结构)
2. enable_milvus=True 时, 直接调用 _retrieve_from_milvus() 验证与 Milvus 的集成是否正常
   (即使没有向量数据, 也应当至少不报错, 能返回空列表)
"""

import asyncio
import io
import os
import sys
from datetime import timedelta

from asgiref.sync import sync_to_async

# 修复 Windows 控制台编码问题 (避免 UnicodeEncodeError)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

# 初始化 Django 环境（用于真实数据库 / 文档 & 作业模型）
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Lumina.settings")
import django  # noqa: E402

django.setup()

from agent.retriever_agent import RetrieverAgent  # noqa: E402


async def test_db_path_only():
    """
    测试 1: enable_milvus=False，仅「标准答案 + 关键点」检索逻辑

    为避免依赖真实数据库，这里使用 Mock 的 _get_question_data，
    专注验证 retrieve() 的返回字段结构与 Milvus 开关逻辑。
    """
    print("\n" + "=" * 60)
    print("测试 1: enable_milvus=False，仅标准答案/关键点检索 (Mock DB)")
    print("=" * 60)

    agent = RetrieverAgent(enable_milvus=False)

    async def fake_get_question_data(assignment_id: int, question_id: int) -> dict:
        """模拟数据库返回的数据结构"""
        return {
            "standard_answer": "这是一个模拟的标准答案，用于测试 RetrieverAgent。",
            "answer_keypoints": ["关键点1：定义", "关键点2：步骤", "关键点3：时间复杂度"],
            "is_analyzed": True,
            "question_content": "测试题目内容：什么是冒泡排序？",
            "score": 10,
        }

    # 覆盖真实的数据库访问逻辑，避免依赖 MySQL / Django ORM
    agent._get_question_data = fake_get_question_data  # type: ignore

    try:
        result = await agent.retrieve(
            question="测试题目：什么是冒泡排序？",
            course_id=1,
            question_id=1,
            assignment_id=1,
        )
        print("返回字段类型:", {k: type(v).__name__ for k, v in result.items()})
        print("standard_answer 是否存在:", result.get("standard_answer") is not None)
        print("answer_keypoints 数量:", len(result.get("answer_keypoints", [])))
        print("materials 条数 (预期为 0，因未启用 Milvus):", len(result.get("materials", [])))
    except Exception as e:
        print("调用 retrieve() 时发生异常 (可能是数据库/配置问题):")
        print("  ", repr(e))


async def test_milvus_only():
    """
    测试 2: enable_milvus=True，仅 Milvus 检索

    直接调用 _retrieve_from_milvus:
    - 不依赖数据库 Assignment 表
    - 只要 Milvus 服务和 collection 存在, 即可完成测试
    - 若没有向量数据, 预期返回空列表 []
    """
    print("\n" + "=" * 60)
    print("测试 2: enable_milvus=True，仅 Milvus 检索")
    print("=" * 60)

    agent = RetrieverAgent(enable_milvus=True)

    try:
        materials = await agent._retrieve_from_milvus(
            question="测试题目：什么是冒泡排序？",
            course_id=1,
            top_k=3,
        )
        print("Milvus 返回 materials 条数:", len(materials))
        if materials:
            from pprint import pprint

            print("示例一条结果:")
            pprint(materials[0])
    except Exception as e:
        print("调用 _retrieve_from_milvus() 时发生异常:")
        print("  ", repr(e))


async def test_with_mysql_and_milvus():
    """
    测试 3: 向 MySQL 写入 Course/Assignment/Document，并向 Milvus 写入文档，
    然后通过 RetrieverAgent 在真实数据上进行一次完整检索。

    步骤：
    1. 创建教师用户 + 课程
    2. 创建带标准答案的 Assignment（questions JSON）
    3. 创建 Document 记录，并构造一条与课程相关的参考文档写入 Milvus
    4. 调用 RetrieverAgent.retrieve，验证标准答案 & materials 是否返回
    """
    print("\n" + "=" * 60)
    print("测试 3: MySQL + Milvus 端到端检索")
    print("=" * 60)

    from django.utils import timezone
    from user.models import UserModel
    from course.models import Course, Assignment, Document
    from langchain_core.documents import Document as LCDocument
    from utils.langchain_milvus_manager import LangChainMilvusManager

    # 1. 创建教师用户和课程（使用 sync_to_async 包装同步 ORM）
    now = timezone.now()
    teacher = await sync_to_async(UserModel.objects.create)(
        username=f"retriever_test_teacher_{now.timestamp()}",
        password="hashed_pw",
        nickname="检索测试教师",
        user_type=UserModel.TEACHER,
        status=UserModel.ENABLED,
        is_deleted=UserModel.NOT_DELETED,
    )

    course = await sync_to_async(Course.objects.create)(
        teacher=teacher,
        course_name="检索集成测试课程",
        course_description="用于 RetrieverAgent + Milvus 集成测试",
        invite_code=f"RTEST{int(now.timestamp())}",
        status=1,
        is_deleted=False,
    )

    # 2. 创建带标准答案的 Assignment（只需一题）
    question_content = "请解释什么是冒泡排序算法，并给出时间复杂度分析。"
    standard_answer = (
        "冒泡排序是一种简单的比较排序算法，通过重复遍历待排序序列，"
        "比较相邻元素并在顺序错误时交换，使得较大的元素逐步“冒泡”到序列末尾。"
        "最坏和平均时间复杂度为 O(n^2)，最好情况（已基本有序且带有优化）可达 O(n)。"
    )
    questions = [
        {
            "id": 1,
            "content": question_content,
            "score": 10,
            "standard_answer": standard_answer,
        }
    ]

    assignment = await sync_to_async(Assignment.objects.create)(
        course=course,
        teacher=teacher,
        title="冒泡排序测试作业",
        description="用于检索 Agent 集成测试的单题作业",
        questions=questions,
        total_score=10,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(days=7),
        assignment_status=1,  # 已发布
        is_deleted=False,
    )

    # 3. 创建 Document 记录（MySQL），并将一段与本课程相关的文本写入 Milvus
    doc_text = (
        "本节课主要讲解冒泡排序算法：通过多次遍历数组，比较相邻元素并交换，"
        "每一轮遍历后，当前未排序部分的最大元素会移动到末尾。"
        "同时我们还分析了算法的时间复杂度和空间复杂度，并与快速排序进行了简要对比。"
    )

    document = await sync_to_async(Document.objects.create)(
        course=course,
        uploader=teacher,
        file_name="bubble_sort_notes.md",
        stored_path="test/path/bubble_sort_notes.md",
        file_size=len(doc_text.encode("utf-8")),
        file_type="md",
        mime_type="text/markdown",
        document_status=1,
        is_deleted=False,
    )

    # 写入一条与该课程相关的向量文档到 Milvus，metadata 中带上 course_id & document_id
    milvus_manager = LangChainMilvusManager(
        collection_name="documents",
        embedding_model="all-MiniLM-L6-v2",
    )
    lc_doc = LCDocument(
        page_content=doc_text,
        metadata={
            "course_id": course.id,
            "document_id": document.id,
            "file_name": document.file_name,
            "source": "retriever_agent_test",
        },
    )
    try:
        milvus_ids = milvus_manager.add_documents([lc_doc])
        print(f"已向 Milvus 写入 {len(milvus_ids)} 条文档，course_id={course.id}")
    except Exception as e:
        print("向 Milvus 写入文档失败（后续检索可能无参考资料）:")
        print("  ", repr(e))

    # 4. 调用 RetrieverAgent.retrieve，在真实 MySQL + Milvus 数据上进行一次检索
    agent = RetrieverAgent(enable_milvus=True)
    try:
        result = await agent.retrieve(
            question=question_content,
            course_id=course.id,
            question_id=1,
            assignment_id=assignment.id,
        )
        print("RetrieverAgent 返回字段类型:", {k: type(v).__name__ for k, v in result.items()})
        print("standard_answer 前 40 字:",
              (result.get("standard_answer") or "")[:40])
        print("answer_keypoints 数量:", len(result.get("answer_keypoints", [])))
        print("materials 条数:", len(result.get("materials", [])))
        if result.get("materials"):
            from pprint import pprint

            print("示例一条 materials:")
            pprint(result["materials"][0])
    except Exception as e:
        print("调用 RetrieverAgent.retrieve() 时发生异常:")
        print("  ", repr(e))


async def main():
    await test_db_path_only()
    await test_milvus_only()
    await test_with_mysql_and_milvus()


if __name__ == "__main__":
    asyncio.run(main())

