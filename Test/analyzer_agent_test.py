#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnalyzerAgent 验证测试
测试场景A（标准答案关键点提取）和场景B（学生答案分析+对比）
"""
import asyncio
import os
import sys
import json
import io

# 修复 Windows 终端编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from agent.analyzer_agent import AnalyzerAgent


# ============================================================
# 测试数据
# ============================================================

# 测试题目
TEST_QUESTION = "请解释什么是冒泡排序算法，并分析其时间复杂度。"

# 标准答案（教师提供）
TEST_STANDARD_ANSWER = """
冒泡排序是一种简单的排序算法。它重复地遍历要排序的列表，比较相邻的两个元素，
如果它们的顺序错误就交换它们的位置。遍历列表的工作会重复进行，直到没有再需要交换的元素为止。

算法步骤：
1. 比较相邻的元素，如果前一个比后一个大，就交换它们
2. 对每一对相邻元素做同样的工作，从开始第一对到结尾的最后一对
3. 每一轮遍历后，最大的元素会"冒泡"到列表末尾
4. 重复以上步骤，每次遍历的比较次数减一

时间复杂度分析：
- 最坏情况：O(n²)，当数组完全逆序时
- 最好情况：O(n)，当数组已经有序时（需要优化版本，添加标志位判断是否发生交换）
- 平均情况：O(n²)
空间复杂度为 O(1)，因为只需要一个临时变量用于交换。
"""

# 学生答案（部分正确，有缺失也有冗余）
TEST_STUDENT_ANSWER = """
冒泡排序就是把数组里的数两两比较，大的往后放，小的往前放。
每次遍历都会把最大的数放到最后面，就像气泡一样浮上去，所以叫冒泡排序。

时间复杂度是O(n²)，因为有两层循环。

冒泡排序是最简单的排序算法之一，很适合初学者学习，但在实际开发中很少使用，
因为效率不如快速排序和归并排序。
"""


def print_section(title: str):
    """打印分隔标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(data: dict):
    """格式化打印结果字典"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def test_scene_a(analyzer: AnalyzerAgent):
    """
    测试场景A：提取标准答案关键点
    验证点：
    1. 是否成功返回 (success=True)
    2. 关键点数量是否合理 (3-10个)
    3. JSON 格式是否完整
    """
    print_section("场景A 测试：提取标准答案关键点")
    print(f"题目：{TEST_QUESTION}")
    print(f"标准答案长度：{len(TEST_STANDARD_ANSWER)} 字符")
    print("-" * 60)

    result = await analyzer.analyze_standard_answer(
        question=TEST_QUESTION,
        standard_answer=TEST_STANDARD_ANSWER
    )

    print("\n【返回结果】:")
    print_result(result)

    # 验证
    print("\n【验证】:")
    print(f"  success: {result.get('success')}")
    print(f"  关键点数量: {result.get('keypoint_count')}")

    keypoints = result.get("keypoints", [])
    if result.get("success") and len(keypoints) >= 3:
        print("  ✓ 场景A 测试通过")
    else:
        print("  ✗ 场景A 测试失败")

    return result


async def test_scene_b(analyzer: AnalyzerAgent, standard_keypoints: list):
    """
    测试场景B：学生答案分析 + 对比
    验证点：
    1. 是否成功提取学生关键点
    2. 对比结果是否有 matching / missing / redundant
    3. 覆盖率是否合理
    """
    print_section("场景B 测试：学生答案分析 + 对比")
    print(f"题目：{TEST_QUESTION}")
    print(f"学生答案长度：{len(TEST_STUDENT_ANSWER)} 字符")
    print(f"标准关键点数量：{len(standard_keypoints)} 个")
    print("-" * 60)

    result = await analyzer.analyze_student_answer(
        question=TEST_QUESTION,
        student_answer=TEST_STUDENT_ANSWER,
        standard_keypoints=standard_keypoints,
        reference_materials=None
    )

    print("\n【返回结果】:")
    print_result(result)

    # 验证
    print("\n【验证】:")
    print(f"  success: {result.get('success')}")
    print(f"  学生关键点数: {len(result.get('student_keypoints', []))}")
    print(f"  匹配数: {len(result.get('matching_keypoints', []))}")
    print(f"  缺失数: {len(result.get('missing_keypoints', []))}")
    print(f"  冗余数: {len(result.get('redundant_keypoints', []))}")
    print(f"  覆盖率: {result.get('coverage_rate', 0)}")

    if result.get("success"):
        print("  ✓ 场景B 测试通过")
    else:
        print("  ✗ 场景B 测试失败")

    return result


async def test_edge_case_empty(analyzer: AnalyzerAgent, standard_keypoints: list):
    """
    边界测试：空答案
    """
    print_section("边界测试：空答案")

    result = await analyzer.analyze_student_answer(
        question=TEST_QUESTION,
        student_answer="",
        standard_keypoints=standard_keypoints,
        reference_materials=None
    )

    print("\n【返回结果】:")
    print_result(result)

    print("\n【验证】:")
    missing_count = len(result.get("missing_keypoints", []))
    print(f"  缺失关键点数: {missing_count} (期望接近标准关键点总数)")
    print(f"  覆盖率: {result.get('coverage_rate', 0)} (期望接近 0)")


async def main():
    print_section("AnalyzerAgent 验证测试开始")

    # 初始化
    print("正在初始化 AnalyzerAgent...")
    analyzer = AnalyzerAgent(provider="qwen")
    print("初始化完成\n")

    # 场景A
    scene_a_result = await test_scene_a(analyzer)
    standard_keypoints = scene_a_result.get("keypoints", [])

    if not standard_keypoints:
        print("\n场景A 未提取到关键点，无法继续场景B 测试")
        return

    # 场景B
    await test_scene_b(analyzer, standard_keypoints)

    # 边界测试
    await test_edge_case_empty(analyzer, standard_keypoints)

    print_section("所有测试完成")


if __name__ == "__main__":
    asyncio.run(main())
