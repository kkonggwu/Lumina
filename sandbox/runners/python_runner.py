#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python test runner.

The runner executes submitted code in a short-lived isolated Python process.
It is intentionally fronted by SandboxService so the process implementation can
be replaced with a Docker worker on the server without changing grading logic.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from sandbox.models import SandboxResult, TestCaseResult

MAX_OUTPUT_CHARS = 4000
DEFAULT_TIMEOUT_MS = 2000


def run_python_tests(student_code: str, test_cases: List[Dict[str, Any]]) -> SandboxResult:
    if not test_cases:
        return SandboxResult(
            status="error",
            passed_count=0,
            total_count=0,
            error="未配置测试用例",
        )

    normalized_cases = [_normalize_case(case, index) for index, case in enumerate(test_cases, 1)]
    timeout_seconds = _overall_timeout_seconds(normalized_cases)

    try:
        with tempfile.TemporaryDirectory(prefix="lumina_py_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "student_solution.py").write_text(student_code or "", encoding="utf-8")
            (tmp_path / "test_harness.py").write_text(_build_harness(normalized_cases), encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, "test_harness.py"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                env=_safe_env(),
            )
    except subprocess.TimeoutExpired as exc:
        return _timeout_result(normalized_cases, exc)
    except Exception as exc:
        return SandboxResult(
            status="error",
            passed_count=0,
            total_count=len(normalized_cases),
            error=f"Python 沙箱启动失败: {exc}",
        )

    stdout = _truncate(completed.stdout)
    stderr = _truncate(completed.stderr)
    parsed = _parse_harness_output(stdout)
    if parsed is None:
        return SandboxResult(
            status="error",
            passed_count=0,
            total_count=len(normalized_cases),
            error="Python 测试进程未返回有效 JSON",
            stdout=stdout,
            stderr=stderr,
        )

    case_results = [
        TestCaseResult(
            case=item.get("case", f"用例 {i + 1}"),
            passed=bool(item.get("passed")),
            input=item.get("input"),
            expected=item.get("expected"),
            actual=item.get("actual"),
            error=item.get("error"),
            stdout=_truncate(item.get("stdout", "")),
            stderr=_truncate(item.get("stderr", "")),
            duration_ms=item.get("duration_ms"),
        )
        for i, item in enumerate(parsed.get("case_results", []))
    ]
    passed_count = sum(1 for item in case_results if item.passed)
    status = "completed" if completed.returncode == 0 or case_results else "error"

    return SandboxResult(
        status=status,
        passed_count=passed_count,
        total_count=len(normalized_cases),
        case_results=case_results,
        error=parsed.get("error"),
        stdout=stdout,
        stderr=stderr,
    )


def _normalize_case(case: Dict[str, Any], index: int) -> Dict[str, Any]:
    if not isinstance(case, dict):
        case = {"input": case}

    expected = case.get("expected", case.get("output", case.get("out")))
    function_name = case.get("function_name") or case.get("entrypoint") or case.get("func")

    return {
        "case": case.get("description") or case.get("desc") or f"用例 {index}",
        "function_name": function_name,
        "input": _parse_value(case.get("input", case.get("in", []))),
        "expected": _parse_value(expected),
        "timeout_ms": int(case.get("timeout_ms") or DEFAULT_TIMEOUT_MS),
    }


def _parse_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text == "":
        return ""
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(text)
        except Exception:
            continue
    return value


def _overall_timeout_seconds(cases: List[Dict[str, Any]]) -> float:
    total_ms = sum(max(100, int(case.get("timeout_ms") or DEFAULT_TIMEOUT_MS)) for case in cases)
    return min(max(total_ms / 1000 + 1, 2), 20)


def _safe_env() -> Dict[str, str]:
    env = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    system_root = os.environ.get("SystemRoot")
    if system_root:
        env["SystemRoot"] = system_root
    return env


def _build_harness(cases: List[Dict[str, Any]]) -> str:
    cases_json = json.dumps(cases, ensure_ascii=False)
    return textwrap.dedent(
        f"""
        # -*- coding: utf-8 -*-
        import contextlib
        import importlib
        import io
        import json
        import time
        import traceback

        CASES = {cases_json}

        def call_function(func, raw_input):
            if isinstance(raw_input, dict):
                return func(**raw_input)
            if isinstance(raw_input, list):
                return func(*raw_input)
            if raw_input == "":
                return func()
            return func(raw_input)

        def main():
            results = []
            module = None
            module_error = None
            try:
                module = importlib.import_module("student_solution")
            except Exception:
                module_error = traceback.format_exc(limit=4)

            for index, case in enumerate(CASES, 1):
                started = time.perf_counter()
                stdout = io.StringIO()
                stderr = io.StringIO()
                actual = None
                error = module_error
                passed = False

                if module is not None:
                    try:
                        function_name = case.get("function_name")
                        if not function_name:
                            public_names = [
                                name for name, value in vars(module).items()
                                if callable(value) and not name.startswith("_")
                            ]
                            if len(public_names) == 1:
                                function_name = public_names[0]
                            else:
                                raise ValueError("测试用例缺少 function_name，且无法唯一推断待测函数")

                        func = getattr(module, function_name)
                        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                            actual = call_function(func, case.get("input"))
                        passed = actual == case.get("expected")
                        error = None
                    except Exception:
                        error = traceback.format_exc(limit=4)

                results.append({{
                    "case": case.get("case") or f"用例 {{index}}",
                    "input": case.get("input"),
                    "expected": case.get("expected"),
                    "actual": actual,
                    "passed": passed,
                    "error": error,
                    "stdout": stdout.getvalue(),
                    "stderr": stderr.getvalue(),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }})

            print(json.dumps({{"case_results": results}}, ensure_ascii=False, default=str))

        if __name__ == "__main__":
            main()
        """
    ).strip()


def _parse_harness_output(stdout: str) -> Optional[Dict[str, Any]]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            data = json.loads(line)
            if isinstance(data, dict) and "case_results" in data:
                return data
        except json.JSONDecodeError:
            continue
    return None


def _timeout_result(cases: List[Dict[str, Any]], exc: subprocess.TimeoutExpired) -> SandboxResult:
    case_results = [
        TestCaseResult(
            case=case.get("case", f"用例 {index}"),
            passed=False,
            input=case.get("input"),
            expected=case.get("expected"),
            error="执行超时",
        )
        for index, case in enumerate(cases, 1)
    ]
    return SandboxResult(
        status="timeout",
        passed_count=0,
        total_count=len(cases),
        case_results=case_results,
        error=f"Python 执行超过限制时间: {exc.timeout}s",
        stdout=_truncate(exc.stdout or ""),
        stderr=_truncate(exc.stderr or ""),
    )


def _truncate(value: Any) -> str:
    text = value if isinstance(value, str) else str(value)
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "...(已截断)"

