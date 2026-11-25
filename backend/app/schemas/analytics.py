"""
app/schemas/analytics.py
─────────────────────────
PURPOSE:
  Phase 8 — Pydantic response schemas for Analytics Dashboard & QA Reports.
  These are READ-ONLY response models. No create/update schemas needed.
"""
from typing import List, Optional
from pydantic import BaseModel


# ── Per-run bar chart row ────────────────────────────────────────────────────
class RunPassFailBar(BaseModel):
    run_key: str
    run_name: str
    status: str
    environment: str
    passed_count: int
    failed_count: int
    blocked_count: int
    skipped_count: int
    not_run_count: int
    total_count: int
    pass_rate: float


# ── Bug breakdown schemas ────────────────────────────────────────────────────
class BugSeverityBreakdown(BaseModel):
    critical: int
    high: int
    medium: int
    low: int


class BugStatusBreakdown(BaseModel):
    open: int
    in_progress: int
    resolved: int
    closed: int
    wont_fix: int


# ── Requirement coverage ─────────────────────────────────────────────────────
class UncoveredRequirement(BaseModel):
    req_key: str
    title: str
    priority: str
    status: str


class RequirementCoverage(BaseModel):
    covered: int
    uncovered: int
    coverage_percentage: float
    uncovered_requirements: List[UncoveredRequirement]


# ── Top-level summary card ───────────────────────────────────────────────────
class ProjectSummary(BaseModel):
    total_requirements: int
    total_test_cases: int
    total_test_runs: int
    total_bugs: int
    health_score: float  # 0–100 weighted score


# ── Full dashboard response ──────────────────────────────────────────────────
class AnalyticsDashboardResponse(BaseModel):
    summary: ProjectSummary
    run_history: List[RunPassFailBar]
    bug_severity: BugSeverityBreakdown
    bug_status: BugStatusBreakdown
    requirement_coverage: RequirementCoverage
