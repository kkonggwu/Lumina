#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared result helpers for sandbox runners."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TestCaseResult:
    case: str
    passed: bool
    input: Any = None
    expected: Any = None
    actual: Any = None
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Frontend historically reads `pass`, so keep it as an alias.
        data["pass"] = self.passed
        return data


@dataclass
class SandboxResult:
    status: str
    passed_count: int
    total_count: int
    case_results: List[TestCaseResult] = field(default_factory=list)
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    execution_mode: str = "subprocess"

    @property
    def pass_rate(self) -> float:
        if self.total_count <= 0:
            return 0.0
        return round(self.passed_count / self.total_count, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "passed_count": self.passed_count,
            "total_count": self.total_count,
            "pass_rate": self.pass_rate,
            "case_results": [case.to_dict() for case in self.case_results],
            "error": self.error,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_mode": self.execution_mode,
        }

