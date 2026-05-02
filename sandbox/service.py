#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public sandbox service used by code graders."""

from typing import List, Optional

from sandbox.runners.python_runner import run_python_tests
from sandbox.runners.sql_runner import run_sql_tests


class SandboxService:
    """Stable facade for Python and SQL sandbox execution."""

    @staticmethod
    def run_python(student_code: str, test_cases: Optional[List]) -> dict:
        return run_python_tests(student_code=student_code, test_cases=test_cases or []).to_dict()

    @staticmethod
    def run_sql(student_sql: str, test_cases: Optional[List]) -> dict:
        return run_sql_tests(student_sql=student_sql, test_cases=test_cases or []).to_dict()

