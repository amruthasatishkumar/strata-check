"""Core result types for STRATA checks.

STRATA (A Layered Data Architecture for Reliable Enterprise AI) scores data
on six dimensions: Sourced, Traceable, Retrievable, Aligned, Timely, Audited.
Every check returns a CheckResult; results roll up into a Scorecard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Dimension(str, Enum):
    SOURCED = "Sourced"
    TRACEABLE = "Traceable"
    RETRIEVABLE = "Retrievable"
    ALIGNED = "Aligned"
    TIMELY = "Timely"
    AUDITED = "Audited"


@dataclass(frozen=True)
class CheckResult:
    dimension: Dimension
    check_id: str
    source: str
    score: float  # 0-100
    evidence: str
    fix: str | None = None

    @property
    def passed(self) -> bool:
        return self.score >= 80


@dataclass
class Scorecard:
    results: list[CheckResult] = field(default_factory=list)

    def dimension_score(self, dim: Dimension) -> float | None:
        scores = [r.score for r in self.results if r.dimension == dim]
        return round(sum(scores) / len(scores), 1) if scores else None

    def overall(self) -> float | None:
        dims = [s for d in Dimension if (s := self.dimension_score(d)) is not None]
        return round(sum(dims) / len(dims), 1) if dims else None

    def top_fixes(self, n: int = 5) -> list[CheckResult]:
        failing = [r for r in self.results if r.fix and not r.passed]
        return sorted(failing, key=lambda r: r.score)[:n]
