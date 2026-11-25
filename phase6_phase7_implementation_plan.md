# Phase 6 & Phase 7 Implementation Plan
> **Platform:** AI-Powered Software Testing & Bug Intelligence Platform
> **Status:** PLAN ONLY — Do NOT implement yet.
> **Architecture Pattern:** Repository → Service → Endpoint → Pydantic Schema (Backend) & Standalone Components → Services → Reactive State (Frontend)
> **Target Release:** Phase 6 and Phase 7 of 11

---

## ⚠️ Non-Regression Safeguards (Critical Rule)

Before any line of code is written in Phase 6 or Phase 7, the following contract must be honored:

| Existing Phase | Key Assets to Protect | Safeguard |
| :--- | :--- | :--- |
| Phase 1 (Auth) | `users`, JWT tokens, `auth.guard.ts` | No changes to `users` table schema or token logic. |
| Phase 2 (Organizations) | `organizations`, `organization_members` | No schema changes. Add FK references only. |
| Phase 3 (Projects) | `projects` table | Add relationships only. No column changes. |
| Phase 4 (Requirements) | `requirements`, `acceptance_criteria`, `requirement_documents` | Add `bug_id` nullable FK in Phase 7 only. |
| Phase 5 (Test Cases) | `test_suites`, `test_cases`, `test_steps` | Add `execution_results` relationship. No column changes to existing tables. |
| All Migrations (001–004) | Never modify past migrations | Only add new migration files `005_...` and `006_...`. |
| All Existing Tests | `test_auth.py`, `test_organizations.py`, `test_projects.py`, `test_requirements.py`, `test_test_cases.py` | Zero regressions. All 31 tests must still pass after implementation. |

---

---

# PHASE 6: Test Execution Runs & Results Logging

## 1. What is Phase 6? (Non-Technical Overview)

Imagine a QA team at Swiggy has 200 test cases written in Phase 5. Before releasing a new app version, the team lead says:
> *"Everyone — please run all 200 tests today and record whether each one Passed, Failed, or was Blocked."*

**Phase 6 is the digital version of that process:**
1. The team lead creates a **Test Run** (like a clipboard worksheet): *"Sprint 24 — Full Regression Run"*.
2. They assign specific test cases from Phase 5 to that run.
3. Each tester executes the test cases step by step.
4. After each test, they click **Pass / Fail / Blocked / Skipped** and optionally write failure notes.
5. The system tracks overall progress (e.g., *"180/200 passed, 15 failed, 5 blocked"*).

---

## 2. Database Schema for Phase 6

### Tables:

**`test_runs`** — The execution worksheet:
| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID PK | Unique identifier |
| `project_id` | UUID FK → projects | Which project this run belongs to |
| `run_key` | VARCHAR(50) | Sequential key e.g. `ECOM-RUN-01` |
| `name` | VARCHAR(255) | e.g. "Sprint 24 Regression" |
| `status` | ENUM | `planned, in_progress, completed, aborted` |
| `environment` | ENUM | `local, staging, qa, production` |
| `created_by` | UUID FK → users | Who created this run |
| `started_at` | TIMESTAMPTZ | When execution actually started |
| `completed_at` | TIMESTAMPTZ | When all items were executed |

**`test_run_items`** — One row per test case in a run:
| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID PK | Unique identifier |
| `test_run_id` | UUID FK → test_runs | Which run this belongs to |
| `test_case_id` | UUID FK → test_cases | Which test case to execute |
| `executed_by` | UUID FK → users | Who ran this test case |
| `result` | ENUM | `not_run, passed, failed, blocked, skipped` |
| `failure_notes` | TEXT | Tester's notes if result = failed |
| `actual_duration_minutes` | INTEGER | How long it actually took |
| `executed_at` | TIMESTAMPTZ | Timestamp when tester submitted result |

---

## 3. Backend Implementation Steps

### Step 6.1: Database Models & Migration
**Files to Create:**
- `backend/app/models/test_run.py` → `TestRun`, `TestRunItem` classes + enums (`RunStatus`, `RunEnvironment`, `RunResult`)
- `backend/app/models/__init__.py` → Export new models (non-breaking addition)
- `backend/app/models/test_case.py` → Add `run_items = relationship(...)` (new relationship, no column changes)
- `backend/app/models/project.py` → Add `test_runs = relationship(...)` (new relationship)
- `backend/migrations/versions/005_create_test_runs_tables.py` → `upgrade()` / `downgrade()`

### Step 6.2: Pydantic Schemas
**File to Create:** `backend/app/schemas/test_run.py`
- `TestRunCreate` (name, description, environment, test_case_ids: List[UUID])
- `TestRunUpdate` (name, description, status, environment)
- `TestRunResponse` (full run + progress stats: passed_count, failed_count, total_count)
- `TestRunItemUpdate` (result, failure_notes, actual_duration_minutes)
- `TestRunItemResponse` (item with embedded test case title + steps)
- `TestRunListResponse` (paginated list)

### Step 6.3: Repository Layer
**File to Create:** `backend/app/repositories/test_run_repository.py`
- `get_next_run_key(db, project_id, project_key)` → sequential `PROJ-RUN-01`
- `create_run(db, project_id, run_data, user_id)` → creates run + bulk creates items
- `get_run_by_id(db, run_id, project_id)` → with items + progress aggregation
- `list_runs(db, project_id, filters, skip, limit)` → with status filter
- `update_run(db, run_id, update_data)` → auto-sets `started_at` / `completed_at`
- `update_run_item(db, item_id, result_data, user_id)` → logs `executed_by`, `executed_at`
- `get_run_progress(db, run_id)` → returns `{total, passed, failed, blocked, skipped, not_run}`

### Step 6.4: Service Layer
**File to Create:** `backend/app/services/test_run_service.py`
- Tenant verification: project must belong to user's organization
- Validate all `test_case_ids` belong to the same project
- Auto-transition run: `planned → in_progress` on first item execution
- Auto-transition: `in_progress → completed` when all items are executed
- Prevent duplicate test_case_ids in same run

### Step 6.5: API Endpoints
**File to Create:** `backend/app/api/v1/endpoints/test_runs.py`

| Method | URL | Purpose |
| :--- | :--- | :--- |
| `GET` | `/projects/{project_id}/runs` | List all test runs (with progress counts) |
| `POST` | `/projects/{project_id}/runs` | Create a new test run |
| `GET` | `/projects/{project_id}/runs/{run_id}` | Full run detail with all items |
| `PUT` | `/projects/{project_id}/runs/{run_id}` | Update run metadata/status |
| `DELETE` | `/projects/{project_id}/runs/{run_id}` | Delete a run |
| `GET` | `/projects/{project_id}/runs/{run_id}/items` | List all execution items |
| `PUT` | `/projects/{project_id}/runs/{run_id}/items/{item_id}` | Submit result (Pass/Fail/Blocked) |

**File to Update (non-breaking):** `backend/app/api/v1/router.py` → Mount `test_runs.router`

### Step 6.6: Automated Backend Tests
**File to Create:** `backend/tests/test_test_runs.py` (7 tests)
- `test_create_test_run_and_add_items`
- `test_sequential_run_key_generation`
- `test_submit_pass_result_on_item`
- `test_submit_fail_result_with_notes`
- `test_run_auto_transitions_to_in_progress`
- `test_run_auto_transitions_to_completed`
- `test_tenant_isolation_runs`

---

## 4. Frontend Implementation Steps (Phase 6)

### Step 6.7: Angular Service
**File to Create:** `frontend/src/app/core/services/test-run.service.ts`
- Methods: `listRuns()`, `createRun()`, `getRunDetail()`, `updateRunItem()`, `updateRun()`

### Step 6.8: Test Runs Main Screen
**Files to Create:** `frontend/src/app/features/test-runs/`
- `test-runs.component.ts/.html/.scss` — Table with status badges and progress bars

### Step 6.9: Create Run Dialog
**Files to Create:** `frontend/src/app/features/test-runs/components/run-dialog/`
- Form with: Run Name, Environment, multi-select test case picker from Phase 5

### Step 6.10: Execution Runner Screen
**Files to Create:** `frontend/src/app/features/test-runs/components/run-execution/`
- Split layout: Left = test case list in this run; Right = step-by-step execution panel
- **Pass / Fail / Blocked / Skip** result buttons
- Failure Notes textarea (appears only when **Fail** is selected)
- Real-time progress bar (e.g., *12/20 complete*)

### Step 6.11: Routing & Navigation
- `frontend/src/app/app.routes.ts` → Add `/test-runs` route
- `frontend/src/app/layout/sidebar/sidebar.component.ts` → Enable "Test Runs" link

---

---

# PHASE 7: Bug Tracker & Defect Management

## 1. What is Phase 7? (Non-Technical Overview)

When a tester clicks **Fail** in Phase 6, they found a bug. Phase 7 provides:
1. **Log bugs** with full reproduction steps, severity, and affected component.
2. **Link bugs** to the failed test case (Phase 6) and/or the broken requirement (Phase 4).
3. **Assign** bugs to developers for fixing.
4. **Track bug lifecycle**: `Open → In Progress → Resolved → Closed`.
5. **Filter and manage** bugs by severity, priority, and status.

---

## 2. Database Schema for Phase 7

**`bugs`** — The defect management table:
| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID PK | Unique identifier |
| `project_id` | UUID FK → projects | Which project this bug belongs to |
| `test_run_item_id` | UUID FK → test_run_items (nullable) | Which failed execution item triggered this |
| `test_case_id` | UUID FK → test_cases (nullable) | Which test case exposed this bug |
| `requirement_id` | UUID FK → requirements (nullable) | Which requirement this bug violates |
| `bug_key` | VARCHAR(50) | Sequential key e.g. `ECOM-BUG-01` |
| `title` | VARCHAR(255) | Short bug summary |
| `description` | TEXT | Full description |
| `steps_to_reproduce` | TEXT | Numbered steps to recreate |
| `expected_behavior` | TEXT | What should have happened |
| `actual_behavior` | TEXT | What actually happened |
| `severity` | ENUM | `critical, high, medium, low` |
| `priority` | ENUM | `critical, high, medium, low` |
| `status` | ENUM | `open, in_progress, resolved, closed, wont_fix` |
| `environment` | VARCHAR(100) | Where bug was found (staging/prod) |
| `browser_os` | VARCHAR(255) | e.g. Chrome 120 / Windows 11 |
| `reported_by` | UUID FK → users | Who reported the bug |
| `assigned_to` | UUID FK → users (nullable) | Developer assigned to fix it |
| `reported_at` | TIMESTAMPTZ | When bug was reported |
| `resolved_at` | TIMESTAMPTZ | When bug was resolved |

---

## 3. Backend Implementation Steps (Phase 7)

### Step 7.1: Database Models & Migration
**Files to Create:**
- `backend/app/models/bug.py` → `Bug` class + enums (`BugSeverity`, `BugPriority`, `BugStatus`)
- `backend/app/models/__init__.py` → Export `Bug` (non-breaking addition)
- `backend/app/models/test_case.py` → Add `bugs = relationship(...)` (nullable, non-breaking)
- `backend/app/models/requirement.py` → Add `bugs = relationship(...)` (nullable, non-breaking)
- `backend/app/models/project.py` → Add `bugs = relationship(...)` (new relationship)
- `backend/migrations/versions/006_create_bugs_table.py`

### Step 7.2: Pydantic Schemas
**File to Create:** `backend/app/schemas/bug.py`
- `BugCreate` (title, description, steps_to_reproduce, expected_behavior, actual_behavior, severity, priority, test_case_id, requirement_id, test_run_item_id)
- `BugUpdate` (title, description, status, severity, priority, assigned_to, resolved_at)
- `BugResponse` (full bug with linked test case summary + requirement summary)
- `BugListResponse` (paginated list)
- `BugFilterParams` (status, severity, priority, assigned_to, search, pagination)

### Step 7.3: Repository Layer
**File to Create:** `backend/app/repositories/bug_repository.py`
- `get_next_bug_key(db, project_id, project_key)` → sequential `PROJ-BUG-01`
- `create_bug(db, project_id, bug_data, user_id)`
- `get_bug_by_id(db, bug_id, project_id)`
- `list_bugs(db, project_id, filters, skip, limit)`
- `update_bug(db, bug_id, update_data)` → auto-sets `resolved_at` on status → `resolved`
- `delete_bug(db, bug_id)`
- `get_bug_stats(db, project_id)` → `{total, open, in_progress, resolved, closed}`

### Step 7.4: Service Layer
**File to Create:** `backend/app/services/bug_service.py`
- Tenant verification
- Validate `test_case_id` belongs to same project (if provided)
- Validate `requirement_id` belongs to same project (if provided)
- Validate `test_run_item_id` belongs to same project run (if provided)
- Auto-link: When creating bug from a failed `test_run_item`, auto-populate `test_case_id`

### Step 7.5: API Endpoints
**File to Create:** `backend/app/api/v1/endpoints/bugs.py`

| Method | URL | Purpose |
| :--- | :--- | :--- |
| `GET` | `/projects/{project_id}/bugs` | List bugs with filters |
| `POST` | `/projects/{project_id}/bugs` | Report a new bug |
| `GET` | `/projects/{project_id}/bugs/{bug_id}` | Get bug details |
| `PUT` | `/projects/{project_id}/bugs/{bug_id}` | Update bug status/assignment |
| `DELETE` | `/projects/{project_id}/bugs/{bug_id}` | Delete a bug |
| `GET` | `/projects/{project_id}/bugs/stats` | Bug count by status/severity |
| `POST` | `/projects/{project_id}/runs/{run_id}/items/{item_id}/report-bug` | Quick-create from failed item |

**File to Update (non-breaking):** `backend/app/api/v1/router.py` → Mount `bugs.router`

### Step 7.6: Automated Backend Tests
**File to Create:** `backend/tests/test_bugs.py` (7 tests)
- `test_create_bug_manually`
- `test_create_bug_from_failed_run_item`
- `test_sequential_bug_key_generation`
- `test_update_bug_status_to_resolved`
- `test_list_bugs_with_filters`
- `test_delete_bug`
- `test_tenant_isolation_bugs`

---

## 4. Frontend Implementation Steps (Phase 7)

### Step 7.7: Angular Service
**File to Create:** `frontend/src/app/core/services/bug.service.ts`
- Methods: `listBugs()`, `createBug()`, `getBugDetail()`, `updateBug()`, `deleteBug()`, `getBugStats()`

### Step 7.8: Bug Tracker Main Screen
**Files to Create:** `frontend/src/app/features/bug-tracker/`
- Table with: Bug Key, Title, Severity, Priority, Status, Linked Test Case, Assigned To
- Filter bar: Status, Severity, Priority, Assigned To, Search
- Summary stats cards: `🔴 Open`, `🟡 In Progress`, `🟢 Resolved`

### Step 7.9: Report Bug Dialog
**Files to Create:** `frontend/src/app/features/bug-tracker/components/bug-dialog/`
- Full form: Title, Description, Steps to Reproduce, Expected vs Actual Behavior
- Severity & Priority dropdowns
- Link to Requirement (Phase 4 dropdown) + Link to Test Case (Phase 5 dropdown)
- Environment & Browser/OS fields

### Step 7.10: Bug Detail Panel
**Files to Create:** `frontend/src/app/features/bug-tracker/components/bug-detail/`
- Status update dropdown (Open → In Progress → Resolved → Closed)
- Assign to User field
- Linked Test Case card (clickable, navigates to test case)
- Linked Requirement card (clickable)

### Step 7.11: Quick-Report from Execution Runner
When a tester marks a test run item as **Failed** in Phase 6:
- Show a **"🐛 Report Bug"** button in the execution runner
- Opens pre-filled Bug Dialog with test case name auto-populated

### Step 7.12: Routing & Navigation
- `frontend/src/app/app.routes.ts` → Add `/bug-tracker` route
- `frontend/src/app/layout/sidebar/sidebar.component.ts` → Enable "Bug Tracker" link (currently "SOON")

---

## 5. Full Implementation Order

```
Phase 6:
  Step 1 → Models & Migration 005
  Step 2 → Pydantic Schemas
  Step 3 → Repository Layer
  Step 4 → Service Layer
  Step 5 → API Endpoints
  Step 6 → Backend Tests (7 new tests → total: 38)
  Step 7 → Angular Service
  Step 8 → Test Runs List Screen
  Step 9 → Create Run Dialog
  Step 10 → Execution Runner Screen
  Step 11 → Routing & Navigation

Phase 7:
  Step 1 → Bug Model & Migration 006
  Step 2 → Pydantic Schemas
  Step 3 → Repository Layer
  Step 4 → Service Layer
  Step 5 → API Endpoints + Quick-Create Route
  Step 6 → Backend Tests (7 new tests → total: 45)
  Step 7 → Angular Service
  Step 8 → Bug Tracker Screen
  Step 9 → Report Bug Dialog
  Step 10 → Bug Detail Panel
  Step 11 → Quick-Report from Execution Runner
  Step 12 → Routing & Navigation
```

---

## 6. File Change Summary

### New Files — Phase 6:
| File | Purpose |
| :--- | :--- |
| `backend/app/models/test_run.py` | TestRun & TestRunItem models |
| `backend/migrations/versions/005_create_test_runs_tables.py` | DB migration |
| `backend/app/schemas/test_run.py` | Pydantic schemas |
| `backend/app/repositories/test_run_repository.py` | Data access layer |
| `backend/app/services/test_run_service.py` | Business logic layer |
| `backend/app/api/v1/endpoints/test_runs.py` | REST API endpoints |
| `backend/tests/test_test_runs.py` | 7 automated tests |
| `frontend/.../features/test-runs/` | Full Angular feature folder |
| `frontend/.../services/test-run.service.ts` | Angular HTTP service |

### New Files — Phase 7:
| File | Purpose |
| :--- | :--- |
| `backend/app/models/bug.py` | Bug model |
| `backend/migrations/versions/006_create_bugs_table.py` | DB migration |
| `backend/app/schemas/bug.py` | Pydantic schemas |
| `backend/app/repositories/bug_repository.py` | Data access layer |
| `backend/app/services/bug_service.py` | Business logic layer |
| `backend/app/api/v1/endpoints/bugs.py` | REST API endpoints |
| `backend/tests/test_bugs.py` | 7 automated tests |
| `frontend/.../features/bug-tracker/` | Full Angular feature folder |
| `frontend/.../services/bug.service.ts` | Angular HTTP service |

### Files to Update (Minimal, Non-Breaking):
| File | Change Type |
| :--- | :--- |
| `backend/app/models/test_case.py` | Add `run_items` + `bugs` relationships only |
| `backend/app/models/requirement.py` | Add `bugs` relationship only |
| `backend/app/models/project.py` | Add `test_runs` + `bugs` relationships only |
| `backend/app/models/__init__.py` | Export new models |
| `backend/app/api/v1/router.py` | Mount two new routers |
| `frontend/src/app/app.routes.ts` | Add two new routes |
| `frontend/src/app/layout/sidebar/sidebar.component.ts` | Enable Bug Tracker link |

---

## 7. Expected Test Count After Both Phases

| Test File | Tests |
| :--- | :--- |
| `test_auth.py` | 8 (unchanged) |
| `test_organizations.py` | 8 (unchanged) |
| `test_projects.py` | 8 (unchanged) |
| `test_requirements.py` | 8 (unchanged) |
| `test_test_cases.py` | 7 (unchanged) |
| `test_test_runs.py` | 7 (new in Phase 6) |
| `test_bugs.py` | 7 (new in Phase 7) |
| **Total** | **53 tests** |
