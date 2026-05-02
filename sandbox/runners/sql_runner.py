#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite-based SQL test runner."""

import ast
import json
import sqlite3
import time
from typing import Any, Dict, List

from sandbox.models import SandboxResult, TestCaseResult

MAX_OUTPUT_CHARS = 4000
DEFAULT_TIMEOUT_MS = 2000
SQL_STEP_LIMIT = 100000


def run_sql_tests(student_sql: str, test_cases: List[Dict[str, Any]]) -> SandboxResult:
    if not test_cases:
        return SandboxResult(
            status="error",
            passed_count=0,
            total_count=0,
            error="未配置测试用例",
        )

    results = []
    for index, raw_case in enumerate(test_cases, 1):
        case = _normalize_case(raw_case, index)
        results.append(_run_single_case(student_sql, case))

    passed_count = sum(1 for item in results if item.passed)
    return SandboxResult(
        status="completed",
        passed_count=passed_count,
        total_count=len(results),
        case_results=results,
        execution_mode="sqlite",
    )


def _normalize_case(case: Dict[str, Any], index: int) -> Dict[str, Any]:
    if not isinstance(case, dict):
        case = {"description": str(case)}

    expected = case.get("expected_rows", case.get("expected", case.get("output", [])))
    setup_sql = case.get("setup_sql") or case.get("input") or ""
    return {
        "case": case.get("description") or case.get("desc") or f"用例 {index}",
        "setup_sql": setup_sql,
        "expected_rows": _parse_rows(expected),
        "compare_mode": case.get("compare_mode") or "unordered",
        "timeout_ms": int(case.get("timeout_ms") or DEFAULT_TIMEOUT_MS),
    }


def _run_single_case(student_sql: str, case: Dict[str, Any]) -> TestCaseResult:
    started = time.perf_counter()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    timed_out = False
    deadline = started + max(case["timeout_ms"], 100) / 1000

    def progress_handler():
        nonlocal timed_out
        if time.perf_counter() > deadline:
            timed_out = True
            return 1
        return 0

    conn.set_progress_handler(progress_handler, SQL_STEP_LIMIT)

    try:
        conn.executescript(case["setup_sql"])
        cursor = conn.execute(student_sql)
        actual_rows = [_row_to_plain(row) for row in cursor.fetchall()]
        expected_rows = case["expected_rows"]
        passed = _compare_rows(actual_rows, expected_rows, case["compare_mode"])
        error = "执行超时" if timed_out else None
    except Exception as exc:
        actual_rows = []
        expected_rows = case["expected_rows"]
        passed = False
        error = "执行超时" if timed_out else str(exc)
    finally:
        conn.close()

    return TestCaseResult(
        case=case["case"],
        passed=passed,
        input=_truncate(case["setup_sql"]),
        expected=expected_rows,
        actual=actual_rows,
        error=error,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )


def _parse_rows(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        text = value.strip()
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
                return _ensure_rows(parsed)
            except Exception:
                continue
        return [text]
    return _ensure_rows(value)


def _ensure_rows(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return [value]


def _row_to_plain(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _compare_rows(actual: List[Any], expected: List[Any], compare_mode: str) -> bool:
    if compare_mode == "ordered":
        return actual == expected
    return _canonical_rows(actual) == _canonical_rows(expected)


def _canonical_rows(rows: List[Any]) -> List[str]:
    return sorted(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) for row in rows)


def _truncate(value: Any) -> str:
    text = value if isinstance(value, str) else str(value)
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "...(已截断)"

