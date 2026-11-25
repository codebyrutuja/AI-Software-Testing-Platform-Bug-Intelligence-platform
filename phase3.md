# Phase 3: Organizations & Projects — Implementation Plan

> **Project:** AI-Powered Software Testing & Bug Intelligence Platform  
> **Phase:** 3 — Multi-Tenancy, Workspaces & Project Management  
> **Architecture Pattern:** Clean 3-Tier Layered Architecture (FastAPI + SQLAlchemy + Pydantic + Angular)

---

## 📌 Executive Summary

In **Phase 2**, we implemented authentication, user management, and JWT security tokens.  
In **Phase 3**, we transform the platform into a **multi-tenant collaborative workspace**:
1. **Organizations (Tenants):** Companies or teams that own software projects (e.g., *Acme Corp*).
2. **Organization Members:** Users assigned specific roles within an organization (`owner`, `admin`, `member`, `viewer`).
3. **Projects:** Software systems being tested (e.g., *Mobile Banking App*, *Payment Gateway API*).
4. **Data Isolation (Multi-Tenancy):** Ensuring that users belonging to Company A can never view or modify projects belonging to Company B.
5. **Modern Dashboard Shell:** A persistent Sidebar and Topbar navigation layout replacing the blank post-login experience.

---

## 🎨 Visual Frontend User Experience (What the User Will See)

### 1. Main Navigation Shell (Sidebar + Topbar)

Once logged in, users are greeted with the enterprise application shell:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [🐛 AI Testing Platform]    🏢 [Acme Corp ▾]                  🔍 Search...   [👤 Alice ▾]│  <-- TOPBAR
├──────────────────────┬─────────────────────────────────────────────────────────────────┤
│                      │                                                                 │
│ 📊 Dashboard         │  📁 Projects                                [+ New Project]     │  <-- ACTION HEADER
│                      │  Manage your test suites and repositories                       │
│ 📁 Projects          │                                                                 │
│                      │  ┌─────────────────────────┐  ┌─────────────────────────┐       │
│ 📋 Requirements      │  │ 📱 Mobile Banking App   │  │ 💳 Payment Gateway API  │       │
│                      │  │ Key: MOB                │  │ Key: PAY                │       │
│ 🧪 Test Cases        │  │ 142 Tests | 12 Bugs     │  │ 88 Tests | 2 Bugs       │       │
│                      │  │ Active • Updated 2h ago │  │ Active • Updated 1d ago │       │
│ 🐛 Bug Tracker       │  └─────────────────────────┘  └─────────────────────────┘       │
│                      │                                                                 │
│ ⚙️ Settings          │  ┌─────────────────────────┐                                    │
│                      │  │ 🌐 E-Commerce Webstore  │                                    │
│                      │  │ Key: WEB                │                                    │
│                      │  │ 230 Tests | 0 Bugs      │                                    │
│                      │  │ Active • Updated 3d ago │                                    │
│                      │  └─────────────────────────┘                                    │
│                      │                                                                 │
│  [ Collapse Sidebar ]│                                                                 │
└──────────────────────┴─────────────────────────────────────────────────────────────────┘
     ^ SIDEBAR                              ^ MAIN CONTENT AREA
```

### 2. "Create New Project" Dialog Modal

Clicking `[+ New Project]` opens a clean Material modal dialog:

```text
┌────────────────────────────────────────────────────────┐
│  Create New Project                                [✕] │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Project Name *                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Mobile Banking iOS & Android                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Project Key * (Prefix for test cases & bugs)          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ MOB                                              │  │
│  └──────────────────────────────────────────────────┘  │
│  ℹ️ 2-6 uppercase letters (e.g. MOB, PAY, WEB)          │
│                                                        │
│  Description (Optional)                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Primary mobile client test suite for 2026       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
├────────────────────────────────────────────────────────┤
│                          [Cancel]  [Create Project]    │
└────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Architecture & Entity Relationships

```text
┌──────────────────────┐         ┌───────────────────────────────┐
│     organizations    │1       *│     organization_members      │
├──────────────────────┼─────────┼───────────────────────────────┤
│ id (UUID PK)         │         │ id (UUID PK)                  │
│ name (VARCHAR)       │         │ organization_id (UUID FK)     │
│ slug (VARCHAR UNIQUE)│         │ user_id (UUID FK)             │
│ is_active (BOOLEAN)  │         │ role (ENUM: owner/admin/...)  │
│ created_at           │         │ joined_at                     │
└──────────┬───────────┘         └───────────────────────────────┘
           │1
           │
           │*
┌──────────▼───────────┐
│       projects       │
├──────────────────────┤
│ id (UUID PK)         │
│ organization_id (FK) │
│ name (VARCHAR)       │
│ key (VARCHAR)        │ (Unique per organization, e.g. MOB)
│ description (TEXT)   │
│ status (ENUM)        │ (active, archived)
│ created_by (UUID FK) │
│ created_at           │
│ updated_at           │
└──────────────────────┘
```

---

## 🛠️ Step-by-Step Implementation Roadmap (Steps 1–15)

### Part A: Database & Migrations (Steps 1–2)

- [ ] **Step 1: Database Models (`models/organization.py`, `models/project.py`)**
  - Implement `Organization`, `OrganizationMember`, and `Project` SQLAlchemy models.
  - Setup relationships, cascaded soft-delete rules, and indexes.
  - Setup `OrgRole` (`owner`, `admin`, `member`, `viewer`) and `ProjectStatus` (`active`, `archived`) enums.

- [ ] **Step 2: Database Migration (`migrations/versions/002_create_orgs_and_projects.py`)**
  - Generate Alembic revision for organizations, organization members, and projects tables.
  - Add unique constraint on `(organization_id, key)` for project prefixes.
  - Run `alembic upgrade head` to apply to PostgreSQL.

---

### Part B: Data Validation, Queries & Business Logic (Steps 3–6)

- [ ] **Step 3: Pydantic Validation Schemas (`schemas/organization.py`, `schemas/project.py`)**
  - Input schemas: `OrganizationCreate`, `OrganizationUpdate`, `ProjectCreate`, `ProjectUpdate`.
  - Output schemas: `OrganizationResponse`, `ProjectResponse`, `MemberResponse`.
  - Field validators enforcing project keys (uppercase alphanumeric, 2-10 characters).

- [ ] **Step 4: Repository Layer (`repositories/organization_repository.py`, `project_repository.py`)**
  - Data access queries: `get_by_id`, `get_by_slug`, `get_user_organizations`, `get_projects_for_org`.
  - Transaction-safe creation, updates, and soft deletes.

- [ ] **Step 5: Business Services (`services/organization_service.py`, `project_service.py`)**
  - Business rules: Creator becomes `owner` of the organization automatically.
  - Prevention of duplicate project keys inside the same organization.
  - Organization member invitation and role change logic.

- [ ] **Step 6: Workspace Context & RBAC Dependencies (`api/dependencies.py`)**
  - Header/Query parameter dependency `get_current_organization` (resolves active workspace).
  - RBAC dependencies: `require_org_admin`, `require_org_member`.
  - Strict tenant isolation ensuring users cannot access projects outside their active organization.

---

### Part C: API Endpoints & Automated Testing (Steps 7–10)

- [ ] **Step 7: Organization Endpoints (`api/v1/endpoints/organizations.py`)**
  - `POST /api/v1/organizations` — Create a new organization workspace.
  - `GET /api/v1/organizations` — List all organizations the logged-in user belongs to.
  - `GET /api/v1/organizations/{id}` — Get workspace details.
  - `POST /api/v1/organizations/{id}/members` — Add/invite a team member.

- [ ] **Step 8: Project Endpoints (`api/v1/endpoints/projects.py`)**
  - `POST /api/v1/organizations/{org_id}/projects` — Create project inside an organization.
  - `GET /api/v1/organizations/{org_id}/projects` — List all projects (with search & pagination).
  - `GET /api/v1/projects/{id}` — Retrieve project details.
  - `PATCH /api/v1/projects/{id}` — Update project name or description.
  - `DELETE /api/v1/projects/{id}` — Archive or soft-delete a project.

- [ ] **Step 9: Router Integration & App Wiring (`api/v1/router.py`)**
  - Mount `/organizations` and `/projects` endpoints into the master `/api/v1` API router.
  - Verify OpenAPI Swagger documentation generated at `http://localhost:8000/docs`.

- [ ] **Step 10: Backend Automated Pytest Suite (`tests/test_projects.py`)**
  - Automated tests for organization creation and member assignment.
  - Multi-tenancy leak test: Verify User A in Org 1 cannot read projects from Org 2.
  - Duplicate project key collision rejection tests.

---

### Part D: Frontend Workspace Layout & Features (Steps 11–15)

- [ ] **Step 11: Main Application Shell (`frontend/src/app/layout/`)**
  - Build persistent **Sidebar** with active navigation links (Dashboard, Projects, Test Cases, Bugs, Settings).
  - Build **Topbar** with application logo, search bar, and profile dropdown.
  - Setup responsive collapsible layout with Angular Material.

- [ ] **Step 12: Angular State Services (`core/services/organization.service.ts`, `project.service.ts`)**
  - State management for the active organization (`activeOrgSubject`).
  - HTTP methods for fetching, creating, and switching organizations and projects.

- [ ] **Step 13: Organization Switcher Dropdown (`layout/topbar/org-switcher/`)**
  - Interactive topbar dropdown showing the current organization with a checkmark.
  - Option to create a new organization directly from the dropdown.

- [ ] **Step 14: Projects Grid & Project Card Components (`features/projects/`)**
  - Project gallery page (`/projects`) showing all projects for the active organization.
  - Reusable `ProjectCardComponent` displaying project name, key badge, test stats, and edit actions.

- [ ] **Step 15: "Create Project" Modal & Reactive Form (`features/projects/project-dialog/`)**
  - Dialog modal using Angular Material (`MatDialog`).
  - Reactive form with instant validation (name required, key pattern `[A-Z]{2,10}`).
  - Instant UI update upon successful project creation.

---

## 📋 REST API Specification Reference

| Method | Endpoint | Description | Access Level |
|---|---|---|---|
| `POST` | `/api/v1/organizations` | Create a new organization workspace | Authenticated User |
| `GET` | `/api/v1/organizations` | List all organizations user belongs to | Authenticated User |
| `GET` | `/api/v1/organizations/{id}` | Get organization details | Org Member |
| `PATCH` | `/api/v1/organizations/{id}` | Update organization settings | Org Admin/Owner |
| `POST` | `/api/v1/organizations/{id}/members` | Add user to organization | Org Admin/Owner |
| `POST` | `/api/v1/organizations/{id}/projects` | Create a new software project | Org Admin/Member |
| `GET` | `/api/v1/organizations/{id}/projects` | List projects for organization | Org Member |
| `GET` | `/api/v1/projects/{id}` | Get single project details | Org Member |
| `PATCH` | `/api/v1/projects/{id}` | Edit project name / description | Org Admin/Member |
| `DELETE` | `/api/v1/projects/{id}` | Archive / delete project | Org Admin/Owner |

---

## 🎯 Verification Criteria for Phase 3 Completion

1. **Database:** Tables `organizations`, `organization_members`, and `projects` exist in PostgreSQL with proper foreign keys.
2. **Multi-Tenancy:** A user belonging only to *Company A* receives a `403 Forbidden` if they try to access *Company B's* project ID.
3. **Automated Tests:** All Pytest tests in `tests/test_projects.py` pass (`100%`).
4. **Frontend Shell:** Logging in navigates to the dashboard with the Topbar and Sidebar visible.
5. **UI Workflow:** The user can create an organization, switch organizations, and create a new project via the modal dialog without page reloads.
