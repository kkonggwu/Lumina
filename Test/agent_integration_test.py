#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 包集成测试
逐步测试 ScorerAgent → AnalyzerAgent → ReporterAgent → CoordinatorAgent 完整流程
"""
import asyncio
import os
import sys
import json
import io
from unittest.mock import AsyncMock

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

# ============================================================
# 公共测试数据
# ============================================================

TEST_QUESTION = "请解释什么是冒泡排序算法，并分析其时间复杂度。"

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
- 最好情况：O(n)，当数组已经有序时
- 平均情况：O(n²)
空间复杂度为 O(1)，因为只需要一个临时变量用于交换。
"""

TEST_STUDENT_ANSWER = """
冒泡排序就是把数组里的数两两比较，大的往后放，小的往前放。
每次遍历都会把最大的数放到最后面，就像气泡一样浮上去，所以叫冒泡排序。

时间复杂度是O(n²)，因为有两层循环。

冒泡排序是最简单的排序算法之一，很适合初学者学习，但在实际开发中很少使用，
因为效率不如快速排序和归并排序。
"""

MOCK_STANDARD_KEYPOINTS = [
    "冒泡排序通过比较相邻元素并交换来实现排序",
    "每轮遍历后最大元素会冒泡到列表末尾",
    "重复遍历直到没有需要交换的元素",
    "最坏时间复杂度为O(n²)",
    "最好时间复杂度为O(n)",
    "空间复杂度为O(1)",
]


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


# ============================================================
# 测试 1: ScorerAgent（纯规则计算，无外部依赖）
# ============================================================
async def test_scorer():
    print_section("测试 1: ScorerAgent")
    from agent.scorer_agent import ScorerAgent

    scorer = ScorerAgent()

    matching_points = [
        {"standard": "冒泡排序通过比较相邻元素并交换来实现排序", "student": "两两比较大的往后放", "match_degree": "medium"},
        {"standard": "每轮遍历后最大元素会冒泡到列表末尾", "student": "把最大的数放到最后面", "match_degree": "high"},
        {"standard": "最坏时间复杂度为O(n²)", "student": "时间复杂度是O(n²)", "match_degree": "high"},
    ]
    missing_points = [
        "重复遍历直到没有需要交换的元素",
        "最好时间复杂度为O(n)",
        "空间复杂度为O(1)",
    ]
    redundant_points = [
        {"content": "冒泡排序很适合初学者学习", "is_valid": True},
        {"content": "效率不如快速排序和归并排序", "is_valid": True},
    ]
    student_keypoints = ["两两比较", "冒泡到末尾", "时间复杂度O(n²)", "适合初学者", "效率比较"]

    result = await scorer.score(
        max_score=10.0,
        missing_points=missing_points,
        redundant_points=redundant_points,
        student_keypoints=student_keypoints,
        standard_keypoints=MOCK_STANDARD_KEYPOINTS,
        matching_points=matching_points,
    )

    print("【评分结果】:")
    print_result(result)

    score = result.get("score", -1)
    confidence = result.get("confidence", -1)
    print(f"\n  得分: {score}/10.0")
    print(f"  置信度: {confidence}")
    print(f"  等级: {result.get('details', {}).get('grade_level', 'N/A')}")

    passed = 0 <= score <= 10 and 0 <= confidence <= 1
    print(f"  {'✓ 通过' if passed else '✗ 失败'}")
    return passed


# ============================================================
# 测试 2: AnalyzerAgent（需要 LLM API）
# ============================================================
async def test_analyzer():
    print_section("测试 2: AnalyzerAgent")
    from agent.analyzer_agent import AnalyzerAgent

    analyzer = AnalyzerAgent(provider="qwen")

    # 场景A：标准答案关键点提取
    print("\n--- 场景A: 标准答案关键点提取 ---")
    result_a = await analyzer.analyze_standard_answer(
        question=TEST_QUESTION,
        standard_answer=TEST_STANDARD_ANSWER,
    )
    print("【场景A结果】:")
    print_result(result_a)

    keypoints = result_a.get("keypoints", [])
    scene_a_ok = result_a.get("success") and len(keypoints) >= 3
    print(f"  提取到 {len(keypoints)} 个关键点 → {'✓ 通过' if scene_a_ok else '✗ 失败'}")

    if not scene_a_ok:
        return False

    # 场景B：学生答案分析+对比
    print("\n--- 场景B: 学生答案分析 + 对比 ---")
    result_b = await analyzer.analyze_student_answer(
        question=TEST_QUESTION,
        student_answer=TEST_STUDENT_ANSWER,
        standard_keypoints=keypoints,
    )
    print("【场景B结果】:")
    print_result(result_b)

    scene_b_ok = result_b.get("success", False)
    matching = len(result_b.get("matching_keypoints", []))
    missing = len(result_b.get("missing_keypoints", []))
    redundant = len(result_b.get("redundant_keypoints", []))
    print(f"  匹配={matching}, 缺失={missing}, 冗余={redundant}, 覆盖率={result_b.get('coverage_rate')}")
    print(f"  {'✓ 通过' if scene_b_ok else '✗ 失败'}")
    return scene_b_ok


# ============================================================
# 测试 3: ReporterAgent（需要 LLM API）
# ============================================================
async def test_reporter():
    print_section("测试 3: ReporterAgent")
    from agent.reporter_agent import ReporterAgent

    reporter = ReporterAgent(provider="qwen")

    scoring_details = {
        "scoring_breakdown": {"base_score": 5.7, "redundant_penalty": 0, "final_score": 5.7, "max_score": 10},
        "keypoint_analysis": {"total_standard": 6, "high_match": 2, "medium_match": 1, "missing_count": 3, "point_value": 1.67},
        "redundant_analysis": {"invalid_count": 0, "valid_count": 2, "total_penalty": 0},
        "grade_level": "及格",
    }

    result = await reporter.report(
        question=TEST_QUESTION,
        student_answer=TEST_STUDENT_ANSWER,
        standard_answer=TEST_STANDARD_ANSWER,
        score=5.7,
        max_score=10.0,
        missing_keypoints=["重复遍历直到无需交换", "最好时间复杂度O(n)", "空间复杂度O(1)"],
        redundant_keypoints=[
            {"content": "适合初学者学习", "is_valid": True},
            {"content": "效率不如快速排序", "is_valid": True},
        ],
        scoring_history=[{"attempt": 1, "score": 5.7, "confidence": 0.75, "timestamp": "2026-02-20T10:00:00", "is_rescore": False}],
        scoring_details=scoring_details,
    )

    print("【报告结果】:")
    print_result(result)

    has_score = result.get("score") is not None
    has_feedback = bool(result.get("feedback"))
    has_suggestions = len(result.get("improvement_suggestions", [])) > 0
    passed = has_score and has_feedback and has_suggestions

    print(f"\n  评语: {result.get('feedback', '')[:80]}...")
    print(f"  建议数: {len(result.get('improvement_suggestions', []))}")
    print(f"  {'✓ 通过' if passed else '✗ 失败'}")
    return passed


# ============================================================
# 测试 4: CoordinatorAgent 完整流程（Mock Retriever 绕过数据库）
# ============================================================
async def test_coordinator():
    print_section("测试 4: CoordinatorAgent 完整流程")
    from agent.coordinator_agent import CoordinatorAgent

    coordinator = CoordinatorAgent()

    mock_retrieve_result = {
        "standard_answer": TEST_STANDARD_ANSWER,
        "answer_keypoints": MOCK_STANDARD_KEYPOINTS,
        "is_analyzed": True,
        "materials": [],
    }
    coordinator.retriever.retrieve = AsyncMock(return_value=mock_retrieve_result)

    print("已 Mock RetrieverAgent.retrieve()，绕过数据库依赖")
    print(f"题目: {TEST_QUESTION}")
    print(f"满分: 10.0")
    print("开始执行完整判题流程...\n")

    result = await coordinator.grade(
        question=TEST_QUESTION,
        student_answer=TEST_STUDENT_ANSWER,
        course_id=1,
        question_id=1,
        assignment_id=1,
        max_score=10.0,
    )

    print("【完整流程结果】:")
    print_result(result)

    status = result.get("status")
    score = result.get("score")
    report = result.get("report")

    print(f"\n  最终状态: {status}")
    print(f"  最终得分: {score}/10.0")
    print(f"  置信度: {result.get('confidence')}")
    print(f"  评分历史轮次: {len(result.get('scoring_history', []))}")

    if report and not report.get("error"):
        print(f"  报告评语: {report.get('feedback', '')[:80]}...")

    passed = status == "completed" and score is not None
    if status == "error":
        print(f"  错误信息: {result.get('error_message')}")
        passed = False

    print(f"  {'✓ 通过' if passed else '✗ 失败（见上方错误信息）'}")
    return passed


# ============================================================
# 主入口
# ============================================================
async def main():
    print_section("Agent 包集成测试")

    results = {}

    # 测试 1: ScorerAgent（无外部依赖）
    results["ScorerAgent"] = await test_scorer()

    # 测试 2: AnalyzerAgent（LLM API）
    results["AnalyzerAgent"] = await test_analyzer()

    # 测试 3: ReporterAgent（LLM API）
    results["ReporterAgent"] = await test_reporter()

    # 测试 4: CoordinatorAgent（完整流程）
    results["CoordinatorAgent"] = await test_coordinator()

    # 汇总
    print_section("测试汇总")
    for name, passed in results.items():
        icon = "✓" if passed else "✗"
        print(f"  {icon} {name}")

    total = len(results)
    passed_count = sum(1 for v in results.values() if v)
    print(f"\n  通过 {passed_count}/{total}")

    if passed_count == total:
        print("\n  全部通过！Agent 包初步开发验证完成。")
    else:
        print("\n  存在失败项，请查看上方详细输出。")


if __name__ == "__main__":
    asyncio.run(main())
