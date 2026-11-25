# Phase 8 — Analytics Dashboard & QA Reports
## Implementation Plan

> **Status**: 📋 PLAN ONLY — Not yet implemented
> **Prerequisite Phases**: 1–7 (all completed ✅)
> **Goal**: Replace the existing placeholder dashboard with a live, data-driven analytics screen and add PDF/CSV export for QA reports.
> **Constraint**: Zero breaking changes to Phases 1–7. No new database tables. No schema changes.

---

## 🏗️ Architecture Overview

```
Phase 8 touches:
├── backend/
│   ├── app/api/v1/endpoints/analytics.py        ← NEW: 1 new endpoint file
│   ├── app/repositories/analytics_repository.py ← NEW: SQL aggregation queries
│   ├── app/schemas/analytics.py                 ← NEW: Response schema shapes
│   └── app/api/v1/router.py                     ← EDIT: mount analytics router (3 lines)
│
└── frontend/
    ├── src/app/features/dashboard/              ← EDIT: replace placeholder HTML
    │   ├── dashboard.component.ts               ← EDIT: inject analytics service
    │   ├── dashboard.component.html             ← EDIT: full analytics layout
    │   └── dashboard.component.scss             ← EDIT: chart + card styles
    ├── src/app/core/services/analytics.service.ts ← NEW: HTTP service
    └── package.json                             ← EDIT: add Chart.js (npm install)
```

**No new Angular route is needed** — the existing `/dashboard` route is reused.
**No new database table or Alembic migration is needed** — all data already exists in
`test_runs`, `test_run_items`, `bugs`, `requirements`, and `test_cases` tables.

---

## 📦 New npm Dependency

| Package | Version | Why |
|:--------|:--------|:----|
| `chart.js` | `^4.x` | The industry-standard, lightweight charting library. Zero Angular-specific lock-in. |
| `ng2-charts` | `^6.x` | Official Angular 17 wrapper for Chart.js (Directive-based, no extra config). |

> **Why Chart.js over Angular Material charts?**
> Angular Material does NOT include charts. Chart.js is the most widely used OSS charting library,
> works without Tailwind, and has no server-side dependencies.

---

## 🔙 Backend Plan

### File 1: `backend/app/repositories/analytics_repository.py` *(NEW)*

This file contains **pure SQL aggregation queries** only. It reads from existing tables —
no writes, no schema changes.

#### Queries to implement:

```
1. get_project_summary(project_id, org_id)
   Returns:
     - total_requirements  (COUNT from requirements table)
     - total_test_cases    (COUNT from test_cases table)
     - total_test_runs     (COUNT from test_runs table)
     - total_bugs          (COUNT from bugs table)

2. get_test_run_pass_fail_stats(project_id, org_id)
   Returns per-run breakdown (last 10 runs):
     - run_key, run_name, status, environment
     - passed_count, failed_count, blocked_count, skipped_count, not_run_count, total_count
     - pass_rate (passed / total * 100)

3. get_bug_severity_breakdown(project_id, org_id)
   Returns:
     - critical_count, high_count, medium_count, low_count
     - open_count, in_progress_count, resolved_count, closed_count

4. get_requirement_coverage(project_id, org_id)
   Returns:
     - requirements with at least 1 linked test case  → "covered"
     - requirements with 0 linked test cases          → "uncovered"
     - coverage_percentage

5. get_test_case_status_breakdown(project_id, org_id)
   Returns:
     - active_count, draft_count, deprecated_count

6. get_overall_health_score(project_id, org_id)
   Computed value (0–100) = weighted formula:
     (pass_rate * 0.5) + (coverage_pct * 0.3) + (bug_resolution_rate * 0.2)
```

---

### File 2: `backend/app/schemas/analytics.py` *(NEW)*

Pydantic response models for each query above. Shapes:

```python
class ProjectSummary(BaseModel):
    total_requirements: int
    total_test_cases: int
    total_test_runs: int
    total_bugs: int
    health_score: float          # 0–100

class RunPassFailBar(BaseModel):
    run_key: str
    run_name: str
    passed_count: int
    failed_count: int
    blocked_count: int
    skipped_count: int
    total_count: int
    pass_rate: float

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

class RequirementCoverage(BaseModel):
    covered: int
    uncovered: int
    coverage_percentage: float
    uncovered_requirements: list[dict]   # list of {req_key, title, priority}

class AnalyticsDashboardResponse(BaseModel):
    summary: ProjectSummary
    run_history: list[RunPassFailBar]
    bug_severity: BugSeverityBreakdown
    bug_status: BugStatusBreakdown
    requirement_coverage: RequirementCoverage
```

---

### File 3: `backend/app/api/v1/endpoints/analytics.py` *(NEW)*

One endpoint file with 2 routes:

```
GET /api/v1/analytics/dashboard?project_id={uuid}
  → Returns full AnalyticsDashboardResponse
  → Auth: JWT required
  → Tenant-safe: validates user belongs to org that owns the project

GET /api/v1/analytics/export/csv?project_id={uuid}&type={runs|bugs}
  → Returns a streaming CSV download (StreamingResponse)
  → Uses Python's built-in `csv` module (no extra pip package needed)
  → type=runs   → exports test run pass/fail history
  → type=bugs   → exports bug list with severity, status, links
```

> **PDF Export Note**: PDF generation requires heavy pip packages (e.g., `reportlab`).
> Phase 8 exports **CSV** only from the backend. PDF generation is deferred to Phase 9.

---

### Edit: `backend/app/api/v1/router.py` *(3-line edit only)*

```python
# ADD this import line:
from app.api.v1.endpoints import analytics

# ADD these 5 lines after the bugs router block:
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)
```

No other changes to `router.py`.

---

## 🎨 Frontend Plan

### Step 1: Install Chart.js (npm)

```bash
cd frontend
npm install chart.js ng2-charts
```

---

### Step 2: `frontend/src/app/core/services/analytics.service.ts` *(NEW)*

Angular HTTP service with two methods:

```typescript
getDashboard(projectId: string): Observable<AnalyticsDashboardResponse>
exportCsv(projectId: string, type: 'runs' | 'bugs'): Observable<Blob>
```

The service uses the existing `HttpClient` interceptor (already set up in Phase 2)
so JWT auth is automatic — no extra setup needed.

---

### Step 3: Dashboard Component Changes

#### `dashboard.component.ts` *(EDIT)*

New responsibilities:
- Load `projects` list via existing `ProjectService` (already exists in Phase 3).
- When user picks a project from a dropdown: call `AnalyticsService.getDashboard(projectId)`.
- Store response data into typed properties consumed by the template.
- Trigger CSV export with `exportCsv()` method which uses a browser download link trick.

No changes to `AuthService` or `OrganizationService` wiring already in place.

---

#### `dashboard.component.html` *(EDIT — full replacement of placeholder content)*

New layout (described as wireframe):

```
┌─────────────────────────────────────────────────────────────────┐
│  ANALYTICS DASHBOARD                        [Project: Dropdown▾] │
│  Your QA health at a glance                 [Export CSV ▾]       │
└─────────────────────────────────────────────────────────────────┘

┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐
│ 🏆 Health  │ │ 📋 Reqs    │ │ 🔬 Cases   │ │ ▶ Runs     │ │ 🐞 Bugs      │
│  Score     │ │   Total    │ │   Total    │ │   Total    │ │   Total      │
│  87 / 100  │ │     12     │ │     45     │ │      8     │ │      3       │
└────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────────┘

┌─────────────────────────────────────┐  ┌───────────────────────────────────┐
│  TEST RUN PASS/FAIL HISTORY         │  │  BUG SEVERITY DISTRIBUTION        │
│  (Grouped Bar Chart — last 10 runs) │  │  (Doughnut / Pie Chart)           │
│                                     │  │   🔴 Critical: 1                  │
│  RUN-01 ████░░ 80% Pass             │  │   🟠 High: 2                      │
│  RUN-02 ██░░░░ 40% Pass             │  │   🟡 Medium: 3                    │
│  RUN-03 ██████ 100% Pass            │  │   🟢 Low: 1                       │
└─────────────────────────────────────┘  └───────────────────────────────────┘

┌─────────────────────────────────────┐  ┌───────────────────────────────────┐
│  REQUIREMENT COVERAGE               │  │  BUG STATUS LIFECYCLE             │
│  (Progress ring / Donut)            │  │  (Horizontal stacked bar)         │
│     [ 73% ]  ← Covered              │  │  🔴 Open        4                 │
│   8 covered / 11 total              │  │  🟡 In Progress 2                 │
│   3 have NO test cases yet ⚠        │  │  🟢 Resolved    5                 │
│                                     │  │  ⚫ Closed       1                │
└─────────────────────────────────────┘  └───────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  UNCOVERED REQUIREMENTS ⚠️  (Table — only shown if coverage < 100%)         │
│  REQ-KEY    │ Title                        │ Priority  │ Status             │
│  ECOM-REQ-03│ User can reset password       │ HIGH      │ Active             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### `dashboard.component.scss` *(EDIT)*

New styles for:
- 5-column summary cards row (responsive, collapses to 2-col on small screens).
- 2-column chart grid (chart cards with min-height: 300px).
- Uncovered requirements warning table with amber left-border.
- Export button dropdown styling.
- NO Tailwind — all explicit SCSS (consistent with Phase 6/7 pattern).

---

### Step 4: CSV Export Flow (Frontend)

When user clicks **"Export CSV"** → **"Export Test Runs"** or **"Export Bugs"**:

1. Angular calls `AnalyticsService.exportCsv(projectId, type)` → returns `Blob`.
2. Frontend creates a hidden `<a>` element with `URL.createObjectURL(blob)`.
3. Browser triggers native file-save dialog → downloads `qa-report-runs.csv` or `qa-report-bugs.csv`.
4. The temporary object URL is revoked after download.

No server-side PDF library needed. No third-party download service needed.

---

## 📋 Implementation Order (Step-by-Step Sequence)

The implementation should be done in this exact order to allow incremental testing:

| Step | Action | Verifiable When Done |
|:-----|:-------|:---------------------|
| 1 | `npm install chart.js ng2-charts` | `package.json` updated, `node_modules` has `chart.js` |
| 2 | Create `analytics_repository.py` | Python import works, queries run against test DB |
| 3 | Create `analytics.py` (schemas) | Pydantic models load without errors |
| 4 | Create `analytics.py` (endpoint) | FastAPI routes register |
| 5 | Edit `router.py` (mount) | `GET /api/v1/analytics/dashboard` returns 200 in Swagger |
| 6 | Backend smoke test | Curl / Swagger confirms real data returned |
| 7 | Create `analytics.service.ts` | TypeScript compiles cleanly |
| 8 | Edit `dashboard.component.ts` | Properties + methods added, TypeScript compiles |
| 9 | Edit `dashboard.component.html` | Charts render (may show empty state if no project selected) |
| 10 | Edit `dashboard.component.scss` | Cards and chart cards look correct |
| 11 | `ng build` | Zero errors, budget checks pass |
| 12 | Manual browser test | Charts render with data, CSV downloads work |
| 13 | `pytest -v tests/` | All 52 tests pass (45 existing + 7 new) |

---

## 🧪 Testing Plan

### Backend Tests (new file: `backend/tests/test_analytics.py`)

| Test | Description |
|:-----|:------------|
| `test_dashboard_requires_auth` | Unauthenticated GET returns 401. |
| `test_dashboard_tenant_isolation` | User from Org A cannot see Org B project analytics. |
| `test_dashboard_summary_counts` | Returns correct requirement/test case/run/bug totals. |
| `test_requirement_coverage_calculation` | Coverage % is correct (covered / total * 100). |
| `test_bug_severity_breakdown` | Returns correct counts per severity level. |
| `test_csv_export_runs` | CSV export returns Content-Type `text/csv` with correct rows. |
| `test_csv_export_bugs` | CSV export for bugs returns correct headers and rows. |

**Target: 7 new tests → bring total from 45 to 52 passing tests.**

---

### Frontend (manual smoke test checklist)
- [ ] Dashboard loads with no errors when no project selected (shows "Pick a project" empty state).
- [ ] Selecting a project loads all 4 charts with real data.
- [ ] Bar chart shows last 10 runs (or all if fewer than 10).
- [ ] Doughnut chart shows bug severity distribution correctly.
- [ ] Coverage ring shows % and highlights uncovered requirements in warning table.
- [ ] "Export Test Runs CSV" triggers browser download with correct file name.
- [ ] "Export Bugs CSV" triggers browser download with correct file name.
- [ ] All Phase 3–7 sidebar links still work (no routing regressions).
- [ ] `ng build` passes with zero errors.

---

## ⚠️ Constraints & Guardrails

| Constraint | How it is enforced |
|:-----------|:-------------------|
| No new database tables | All queries read from existing Phase 3–7 tables only |
| No Alembic migrations | Analytics is a read-only aggregation layer |
| No breaking changes to existing endpoints | New endpoint file; zero edits to existing endpoint files |
| No breaking changes to existing Angular routes | Only `/dashboard` is modified; all Phase 3–7 routes untouched |
| No Tailwind classes | All styles written as explicit SCSS |
| Angular build budget compliance | Verify `ng build` after component edits |
| No new pip dependencies | CSV uses Python `csv` stdlib; charts via `chart.js` (frontend-only) |

---

## 📁 Complete File Change Summary

### Files to CREATE (new — no risk to existing code):
| File | Type |
|:-----|:-----|
| `backend/app/repositories/analytics_repository.py` | Backend |
| `backend/app/schemas/analytics.py` | Backend |
| `backend/app/api/v1/endpoints/analytics.py` | Backend |
| `backend/tests/test_analytics.py` | Backend Tests |
| `frontend/src/app/core/services/analytics.service.ts` | Frontend |

### Files to EDIT (minimal, surgical edits only):
| File | Edit Description |
|:-----|:----------------|
| `backend/app/api/v1/router.py` | +3 lines: import + include_router for analytics |
| `frontend/src/app/features/dashboard/dashboard.component.ts` | Replace 30-line placeholder with analytics-wired component |
| `frontend/src/app/features/dashboard/dashboard.component.html` | Replace 52-line placeholder with full analytics layout |
| `frontend/src/app/features/dashboard/dashboard.component.scss` | Add chart card and summary card styles |
| `frontend/package.json` | Add `chart.js` and `ng2-charts` to dependencies |

### Files NOT touched (guaranteed zero changes):
- All Phase 3–7 component files (projects, requirements, test-cases, test-runs, bug-tracker)
- All existing endpoint files (`bugs.py`, `test_runs.py`, `requirements.py`, etc.)
- All existing models, migrations, repositories, services
- `sidebar.component.ts`, `app.routes.ts`, auth interceptor, `app.component.ts`
- All 45 existing test files

---

## ⏱️ Estimated Effort

| Area | Estimated Time |
|:-----|:--------------|
| Backend: Repository queries + schema + endpoint | ~2–3 hours |
| Frontend: Analytics service + dashboard rewrite | ~3–4 hours |
| Testing: 7 new backend tests + manual smoke test | ~1–2 hours |
| **Total** | **~6–9 hours of focused implementation** |
