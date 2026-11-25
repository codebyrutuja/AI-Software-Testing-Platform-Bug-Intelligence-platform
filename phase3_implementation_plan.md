# Phase 3 — Detailed Implementation Plan
## Organizations & Projects (Multi-Tenant Workspaces)

> **Codebase Analyzed:** Phase 2 fully implemented and verified.
> **Architecture:** FastAPI + SQLAlchemy + Pydantic + Angular 17 Standalone
> **Pattern to follow:** Identical to Phase 2 — Repository → Service → Endpoint → Schema
> **Status:** PLAN ONLY — Nothing implemented yet.

---

## Codebase Analysis Summary (What Phase 2 Left Us)

### Backend (Ready to extend)
| File | Purpose | Phase 3 Impact |
|---|---|---|
| `app/core/database.py` | SQLAlchemy engine + `get_db()` + `Base` | Phase 3 models inherit from same `Base` ✅ |
| `app/core/config.py` | Pydantic settings from `.env` | No changes needed ✅ |
| `app/core/security.py` | JWT + bcrypt | No changes needed ✅ |
| `app/models/user.py` | `User` model + `UserRole` enum | Phase 3 models add FK to `users.id` ✅ |
| `app/repositories/user_repository.py` | All User DB queries | Unchanged ✅ |
| `app/services/auth_service.py` | Auth business logic | Unchanged ✅ |
| `app/api/dependencies.py` | `get_current_user`, `require_superadmin` | We ADD new org-level deps here 🆕 |
| `app/api/v1/router.py` | Master router (auth, users, health) | We ADD org + project routers here 🆕 |
| `migrations/versions/001_create_users_table.py` | First Alembic migration | We ADD `002_create_orgs_and_projects.py` 🆕 |

### Frontend (Ready to extend)
| File | Purpose | Phase 3 Impact |
|---|---|---|
| `app.config.ts` | Providers: router, HttpClient+interceptor, animations | No changes needed ✅ |
| `app.routes.ts` | Routes: /login, /register, /dashboard | We ADD shell route + /projects 🆕 |
| `core/services/auth.service.ts` | Login, logout, currentUser$ BehaviorSubject | Unchanged ✅ |
| `core/interceptors/auth.interceptor.ts` | Auto-attach JWT header to all requests | Unchanged ✅ |
| `core/guards/auth.guard.ts` | Redirect unauthenticated users to /login | Unchanged ✅ |

---

## Database Schema to Create

```sql
-- Table 1: organizations
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: organization_members
CREATE TABLE organization_members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            orgrole NOT NULL DEFAULT 'member',
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- Table 3: projects
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    key             VARCHAR(10) NOT NULL,
    description     TEXT,
    status          projectstatus NOT NULL DEFAULT 'active',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, key)
);
```

---

## Step-by-Step Implementation Plan

### PART A — Database & Models (Steps 1–2)

#### Step 1 — SQLAlchemy Models
**Files to CREATE:**
- `backend/app/models/organization.py` — Organization, OrganizationMember classes + OrgRole enum
- `backend/app/models/project.py` — Project class + ProjectStatus enum

**Files to UPDATE:**
- `backend/app/models/__init__.py` — Import new models so Alembic discovers them

**Models to implement:**

`organization.py`:
- `OrgRole` class: OWNER, ADMIN, MEMBER, VIEWER
- `Organization(Base)`: id(UUID PK), name, slug(UNIQUE), description, is_active, created_by(FK→users), created_at, updated_at
- `OrganizationMember(Base)`: id(UUID PK), organization_id(FK→organizations CASCADE), user_id(FK→users CASCADE), role(Enum), joined_at + UniqueConstraint(org_id, user_id)

`project.py`:
- `ProjectStatus` class: ACTIVE, ARCHIVED
- `Project(Base)`: id(UUID PK), organization_id(FK→organizations CASCADE), name, key(VARCHAR 10), description, status(Enum), created_by(FK→users), created_at, updated_at + UniqueConstraint(org_id, key)

**Verification:** `python -c "from app.models.organization import Organization; print('OK')"` → no error

---

#### Step 2 — Alembic Migration
**File to CREATE:**
- `backend/migrations/versions/002_create_orgs_and_projects.py`

**Key settings:**
- `revision = "002"`
- `down_revision = "001"` (chains from Phase 2)

**upgrade() must:**
1. Create `orgrole` PostgreSQL ENUM (owner, admin, member, viewer)
2. Create `projectstatus` PostgreSQL ENUM (active, archived)
3. Create `organizations` table
4. Create `organization_members` table with UniqueConstraint
5. Create `projects` table with UniqueConstraint on (organization_id, key)
6. Add indexes on slug, organization_id columns

**downgrade() must:** Drop tables in reverse order, then drop ENUM types

**Verification:**
```bash
cd backend && alembic upgrade head
# psql: \dt → shows organizations, organization_members, projects tables
```

---

### PART B — Validation Schemas (Step 3)

#### Step 3 — Pydantic Schemas
**Files to CREATE:**
- `backend/app/schemas/organization.py`
- `backend/app/schemas/project.py`

**organization.py schemas:**
- `OrganizationCreate`: name(min 2), description(optional) — slug auto-generated by service
- `OrganizationUpdate`: name(optional), description(optional)
- `OrganizationResponse`: id, name, slug, description, is_active, created_by, timestamps + `model_config = {"from_attributes": True}`
- `MemberResponse`: id, user_id, role, joined_at + `model_config = {"from_attributes": True}`
- `AddMemberRequest`: email(EmailStr), role(default="member")
- `UserSummary`: id, email, full_name (lightweight user info for embedding)

**project.py schemas:**
- `ProjectCreate`: name(min 2, max 255), key(min 2, max 10 + @field_validator to enforce uppercase letters only), description(optional)
- `ProjectUpdate`: name(optional), description(optional), status(optional)
- `ProjectResponse`: id, organization_id, name, key, description, status, created_by, timestamps + `model_config = {"from_attributes": True}`

**Key validator for project key:**
```python
@field_validator("key")
@classmethod
def key_uppercase_only(cls, v):
    import re
    v = v.upper()
    if not re.match(r'^[A-Z]{2,10}$', v):
        raise ValueError("Project key must be 2-10 uppercase letters (e.g. MOB, PAY, WEB)")
    return v
```

---

### PART C — Repositories (Step 4)

#### Step 4 — Repository Layer
**Files to CREATE:**
- `backend/app/repositories/organization_repository.py`
- `backend/app/repositories/project_repository.py`

**Follow SAME pattern as `user_repository.py`** — class with `def __init__(self, db: Session)`

**OrganizationRepository methods:**
- `get_by_id(org_id)` → Optional[Organization]
- `get_by_slug(slug)` → Optional[Organization]
- `get_user_organizations(user_id)` → List[Organization] — JOIN with organization_members
- `get_member(org_id, user_id)` → Optional[OrganizationMember]
- `get_members(org_id)` → List[OrganizationMember]
- `is_member(org_id, user_id)` → bool
- `get_member_role(org_id, user_id)` → Optional[str]
- `create(data, created_by_id)` → Organization — also creates first member with role="owner"
- `add_member(org_id, user_id, role)` → OrganizationMember
- `update(org_id, data)` → Optional[Organization]
- `deactivate(org_id)` → bool (soft delete)

**Slug generation helper (inside create method):**
```python
import re
slug = re.sub(r'[^a-z0-9]+', '-', data.name.lower()).strip('-')
# "Acme Corp" → "acme-corp"
# If slug exists, append counter: "acme-corp-2"
```

**ProjectRepository methods:**
- `get_by_id(project_id)` → Optional[Project]
- `get_by_org(org_id, skip=0, limit=100)` → List[Project]
- `key_exists_in_org(org_id, key)` → bool
- `create(org_id, data, created_by_id)` → Project
- `update(project_id, data)` → Optional[Project]
- `archive(project_id)` → bool (sets status="archived")

---

### PART D — Business Services (Step 5)

#### Step 5 — Service Layer
**Files to CREATE:**
- `backend/app/services/organization_service.py`
- `backend/app/services/project_service.py`

**Follow SAME pattern as `auth_service.py`** — class with `def __init__(self, db: Session)`

**OrganizationService business rules:**
- `create_organization(data, current_user)` → Creator auto-becomes "owner" member
- `add_member(org_id, request, current_user)`:
  - Look up user by email (raise 404 if not found)
  - Check not already a member (raise 409 if duplicate)
  - Add with requested role
- `get_my_organizations(current_user)` → Returns orgs where user is a member
- `get_organization(org_id, current_user)` → Returns org details (member-only)
- `update_organization(org_id, data, current_user)` → Admin/owner only
- `remove_member(org_id, user_id, current_user)` → Owner only; cannot remove self if last owner

**ProjectService business rules:**
- `create_project(org_id, data, current_user)`:
  - Check duplicate key: `if project_repo.key_exists_in_org(org_id, data.key): raise 409`
- `list_projects(org_id, skip, limit)` → List all non-archived projects for org
- `update_project(project_id, data)` → Partial update
- `archive_project(project_id)` → Soft delete (status="archived")

---

### PART E — Dependencies for Multi-Tenancy (Step 6)

#### Step 6 — Extend `dependencies.py`
**File to UPDATE:**
- `backend/app/api/dependencies.py` — ADD 3 new functions, do NOT touch existing ones

**New functions to add:**

```python
def get_organization_member(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrganizationMember:
    """
    TENANT ISOLATION guard.
    Verifies the current user is a member of the requested organization.
    Use on any org-scoped endpoint.
    Returns 403 if user is not a member (never 404 to avoid info leaks).
    """

def require_org_admin(
    membership: OrganizationMember = Depends(get_organization_member),
) -> OrganizationMember:
    """
    Restricts to org admins and owners only.
    Use for: adding members, editing org settings, creating projects.
    """

def require_org_owner(
    membership: OrganizationMember = Depends(get_organization_member),
) -> OrganizationMember:
    """
    Restricts to org owner only.
    Use for: deleting the organization, removing members.
    """
```

**Security contract enforced:**
```
GET /api/v1/organizations/abc123/projects
        → get_organization_member(org_id="abc123", current_user=Alice)
        → Is Alice a member of org abc123?
              YES → pass OrganizationMember into endpoint
              NO  → HTTP 403 "You are not a member of this organization."
```

---

### PART F — API Endpoints (Steps 7–9)

#### Step 7 — Organization Endpoints
**File to CREATE:** `backend/app/api/v1/endpoints/organizations.py`

**Thin endpoints — same pattern as Phase 2 `auth.py`** (delegate everything to service):

| Method | Path | Dependency | Returns |
|---|---|---|---|
| POST | `/` | `get_current_active_user` | OrganizationResponse (201) |
| GET | `/` | `get_current_active_user` | List[OrganizationResponse] |
| GET | `/{org_id}` | `get_organization_member` | OrganizationResponse |
| PATCH | `/{org_id}` | `require_org_admin` | OrganizationResponse |
| GET | `/{org_id}/members` | `get_organization_member` | List[MemberResponse] |
| POST | `/{org_id}/members` | `require_org_admin` | MemberResponse (201) |
| DELETE | `/{org_id}/members/{user_id}` | `require_org_owner` | 204 No Content |

---

#### Step 8 — Project Endpoints
**File to CREATE:** `backend/app/api/v1/endpoints/projects.py`

| Method | Path | Dependency | Returns |
|---|---|---|---|
| POST | `/organizations/{org_id}/projects` | `get_organization_member` | ProjectResponse (201) |
| GET | `/organizations/{org_id}/projects` | `get_organization_member` | List[ProjectResponse] |
| GET | `/projects/{project_id}` | `get_current_active_user` + org check in service | ProjectResponse |
| PATCH | `/projects/{project_id}` | `get_current_active_user` + admin check in service | ProjectResponse |
| DELETE | `/projects/{project_id}` | `get_current_active_user` + admin check in service | 204 No Content |

---

#### Step 9 — Router Wiring
**File to UPDATE:** `backend/app/api/v1/router.py`

Add these lines (keep all existing lines):
```python
from app.api.v1.endpoints import auth, health, users, organizations, projects

api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(projects.router, prefix="", tags=["Projects"])
```

**Verification:** `uvicorn app.main:app --reload` → open `http://localhost:8000/docs` → see Organizations and Projects sections

---

### PART G — Automated Tests (Step 10)

#### Step 10 — Pytest Integration Tests
**Files to CREATE:**
- `backend/tests/test_organizations.py`
- `backend/tests/test_projects.py`

**Reuse existing test infrastructure from `test_auth.py`:** Same SQLite in-memory setup + `app.dependency_overrides[get_db]`

**test_organizations.py cases:**
1. `test_create_organization_success` — returns 201, correct name/slug
2. `test_creator_becomes_owner` — after create, GET members → creator has role="owner"
3. `test_list_my_organizations` — user only sees their own orgs
4. `test_add_member_as_admin` — 201 Created
5. `test_cannot_add_nonexistent_user` — 404
6. `test_cannot_add_duplicate_member` — 409
7. `test_viewer_cannot_add_members` — 403
8. **`test_tenant_isolation`** ← CRITICAL: UserA in Org1 cannot GET Org2 details → 403

**test_projects.py cases:**
1. `test_create_project_success` — returns 201, key auto-uppercased
2. `test_invalid_project_key_rejected` — key with digits → 422
3. `test_duplicate_project_key_rejected` — same key in same org → 409
4. `test_same_key_different_org_allowed` — "MOB" can exist in two different orgs
5. `test_list_projects_paginated` — skip/limit params work
6. `test_archive_project` — status becomes "archived"
7. **`test_non_member_cannot_see_projects`** ← CRITICAL: UserB cannot GET org's projects → 403

**Verification:** `pytest tests/ -v` → all tests green

---

### PART H — Frontend (Steps 11–15)

#### Step 11 — Main Application Shell
**Files to CREATE:**
- `frontend/src/app/layout/shell/shell.component.ts` + `.html` + `.scss`
- `frontend/src/app/layout/sidebar/sidebar.component.ts` + `.html` + `.scss`
- `frontend/src/app/layout/topbar/topbar.component.ts` + `.html` + `.scss`

**Shell HTML structure:**
```html
<div class="app-shell">
  <app-sidebar [isCollapsed]="sidebarCollapsed"></app-sidebar>
  <div class="main-content" [class.collapsed]="sidebarCollapsed">
    <app-topbar (toggleSidebar)="sidebarCollapsed = !sidebarCollapsed"></app-topbar>
    <main class="page-content">
      <router-outlet></router-outlet>
    </main>
  </div>
</div>
```

**Sidebar nav links:**
- 📊 Dashboard → `/dashboard`
- 📁 Projects → `/projects`
- 📋 Requirements → `/requirements` (disabled, future)
- 🧪 Test Cases → `/test-cases` (disabled, future)
- 🐛 Bug Tracker → `/bugs` (disabled, future)
- ⚙️ Settings → `/settings` (disabled, future)

**Topbar elements:**
- Left: 🐛 logo + "AI Testing Platform" text
- Center: Organization switcher dropdown (Step 13)
- Right: 🔍 Search (placeholder) + 👤 User avatar + name + dropdown (Profile link, Sign Out)

---

#### Step 12 — Angular State Services
**Files to CREATE:**
- `frontend/src/app/core/services/organization.service.ts`
- `frontend/src/app/core/services/project.service.ts`

**OrganizationService:**
```typescript
export interface Organization { id, name, slug, description, is_active, created_at, updated_at }
export interface Member { id, user_id, role, joined_at }

@Injectable({ providedIn: 'root' })
export class OrganizationService {
  private activeOrgSubject = new BehaviorSubject<Organization | null>(null);
  activeOrg$ = this.activeOrgSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadSavedActiveOrg(); // Restore from localStorage on app start
  }

  getMyOrganizations(): Observable<Organization[]>  // GET /api/v1/organizations
  createOrganization(data): Observable<Organization> // POST /api/v1/organizations
  addMember(orgId, data): Observable<Member>         // POST /api/v1/organizations/{id}/members
  setActiveOrg(org: Organization): void              // localStorage + BehaviorSubject.next()
  loadSavedActiveOrg(): void                         // localStorage.getItem('active_org')
}
```

**ProjectService:**
```typescript
export interface Project { id, organization_id, name, key, description, status, created_at, updated_at }

@Injectable({ providedIn: 'root' })
export class ProjectService {
  getProjects(orgId: string, skip=0, limit=50): Observable<Project[]>
  createProject(orgId: string, data): Observable<Project>
  getProject(projectId: string): Observable<Project>
  updateProject(projectId: string, data): Observable<Project>
  archiveProject(projectId: string): Observable<void>
}
```

---

#### Step 13 — Organization Switcher in Topbar
**File to UPDATE:** `frontend/src/app/layout/topbar/topbar.component.ts`

**Behavior:**
1. `ngOnInit`: call `OrganizationService.getMyOrganizations()` to populate dropdown list
2. Display active org name + (▾) dropdown arrow using `MatMenu`
3. Dropdown items: each org with ✓ checkmark if active
4. Click org: `setActiveOrg(org)` → `activeOrg$` emits → Projects page auto-reloads via subscription
5. Bottom of dropdown: "＋ Create Organization" → opens `MatDialog` with create org form

---

#### Step 14 — Projects Page & Project Card Component
**Files to CREATE:**
- `frontend/src/app/features/projects/projects.component.ts` + `.html` + `.scss`
- `frontend/src/app/features/projects/project-card/project-card.component.ts` + `.html` + `.scss`

**ProjectsComponent behavior:**
1. Subscribe to `OrganizationService.activeOrg$`
2. When org changes → call `ProjectService.getProjects(org.id)`
3. Show CSS Grid of `ProjectCardComponent` (responsive: 1 → 2 → 3 columns)
4. Show empty state when no projects: illustration + "Create your first project" button
5. `[+ New Project]` button in page header → opens dialog (Step 15)

**ProjectCardComponent inputs:**
```typescript
@Input() project: Project;
// Displays: key badge, name, description, status chip, Created date
// Action: "Open →" button (navigates to future project detail page)
```

---

#### Step 15 — Create Project Dialog + Update Routes
**Files to CREATE:**
- `frontend/src/app/features/projects/project-dialog/project-dialog.component.ts` + `.html`

**Dialog form fields:**
- `name` — required, min 2, max 255 chars
- `key` — required, regex `/^[A-Z]{2,10}$/`, auto-uppercased as user types with `(input)` event
- `description` — optional textarea

**Submit behavior:**
1. Set `isLoading = true`, disable button (same as Login in Phase 2)
2. Call `ProjectService.createProject(activeOrgId, formData)`
3. SUCCESS: Close dialog → `ProjectsComponent` receives new project → appends card to grid immediately (no page reload)
4. ERROR: Show error banner inside dialog (e.g., "Key 'MOB' already exists in this organization")

**File to UPDATE:** `frontend/src/app/app.routes.ts`

```typescript
import { ShellComponent } from './layout/shell/shell.component';

export const routes: Routes = [
  // Public routes (unchanged from Phase 2)
  { path: 'login',    loadComponent: () => import('./features/auth/login/login.component')... },
  { path: 'register', loadComponent: () => import('./features/auth/register/register.component')... },

  // Protected shell with child routes (NEW in Phase 3)
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: 'dashboard', loadComponent: () => import('./features/dashboard/dashboard.component')... },
      { path: 'projects',  loadComponent: () => import('./features/projects/projects.component')... },
      { path: '', redirectTo: 'projects', pathMatch: 'full' },
    ]
  },

  { path: '**', redirectTo: '/login' },
];
```

---

## Complete File List

### Backend Files to CREATE (13 new files)
```
backend/app/models/organization.py
backend/app/models/project.py
backend/app/schemas/organization.py
backend/app/schemas/project.py
backend/app/repositories/organization_repository.py
backend/app/repositories/project_repository.py
backend/app/services/organization_service.py
backend/app/services/project_service.py
backend/app/api/v1/endpoints/organizations.py
backend/app/api/v1/endpoints/projects.py
backend/migrations/versions/002_create_orgs_and_projects.py
backend/tests/test_organizations.py
backend/tests/test_projects.py
```

### Backend Files to UPDATE (3 files)
```
backend/app/models/__init__.py          ← import Organization, OrganizationMember, Project
backend/app/api/dependencies.py         ← add get_organization_member, require_org_admin, require_org_owner
backend/app/api/v1/router.py            ← add organizations + projects routers
```

### Frontend Files to CREATE (10+ new files)
```
frontend/src/app/layout/shell/shell.component.ts (+.html, .scss)
frontend/src/app/layout/sidebar/sidebar.component.ts (+.html, .scss)
frontend/src/app/layout/topbar/topbar.component.ts (+.html, .scss)
frontend/src/app/core/services/organization.service.ts
frontend/src/app/core/services/project.service.ts
frontend/src/app/features/projects/projects.component.ts (+.html, .scss)
frontend/src/app/features/projects/project-card/project-card.component.ts (+.html, .scss)
frontend/src/app/features/projects/project-dialog/project-dialog.component.ts (+.html)
```

### Frontend Files to UPDATE (1 file)
```
frontend/src/app/app.routes.ts          ← Add shell route with children
```

---

## Phase 3 Completion Checklist

### Backend
- [ ] Step 1: Models — Organization, OrganizationMember, Project defined with correct FK relationships
- [ ] Step 2: `alembic upgrade head` runs cleanly, 3 new tables visible in psql
- [ ] Step 3: Schemas — project key auto-uppercased, slug auto-generated from name
- [ ] Step 4: Repositories — all CRUD queries for orgs and projects implemented
- [ ] Step 5: Services — business rules enforced (duplicate key, member isolation, owner protection)
- [ ] Step 6: Dependencies — 3 new functions added without breaking existing get_current_user
- [ ] Step 7: Organization endpoints visible in Swagger at http://localhost:8000/docs
- [ ] Step 8: Project endpoints visible in Swagger at http://localhost:8000/docs
- [ ] Step 9: `uvicorn app.main:app --reload` starts with no ImportError
- [ ] Step 10: `pytest tests/ -v` → ALL tests pass, including tenant isolation tests

### Frontend
- [ ] Step 11: After login, shell with Sidebar + Topbar is visible (not blank page)
- [ ] Step 12: OrganizationService.getMyOrganizations() returns live data from backend
- [ ] Step 13: Org switcher in topbar functions correctly, switching updates project list
- [ ] Step 14: Projects grid renders project cards for the active organization
- [ ] Step 15: Create Project dialog — form validates, new card appears on submit without page reload
