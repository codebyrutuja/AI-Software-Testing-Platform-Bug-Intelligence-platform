# AI-Powered Software Testing & Bug Intelligence Platform

A comprehensive, production-oriented QA management platform built with Angular, FastAPI, and PostgreSQL.

---

## 🚀 Quick Start

### Prerequisites

| Tool | Required Version | Check Command |
|------|-----------------|---------------|
| Python | 3.11, 3.12, or **3.13** | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Angular CLI | 17+ | `ng version` |
| PostgreSQL | 14+ | `psql --version` |
| Git | Any | `git --version` |

> ⚠️ **Python 3.14 is NOT supported yet** — use Python 3.13 or lower.

---

## 📁 Project Structure

```
AI-Powered Software Testing & Bug Intelligence Platform/
├── backend/                    ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py             ← Application entry point
│   │   ├── core/               ← Config, DB, Security, Logging
│   │   ├── api/                ← API routes and endpoints
│   │   ├── models/             ← SQLAlchemy database models
│   │   ├── schemas/            ← Pydantic request/response schemas
│   │   ├── repositories/       ← Database query logic
│   │   ├── services/           ← Business logic
│   │   └── utils/              ← Shared utilities
│   ├── migrations/             ← Alembic database migrations
│   ├── tests/                  ← Pytest tests
│   ├── venv/                   ← Python virtual environment (not in Git)
│   ├── .env                    ← Local environment variables (not in Git)
│   ├── .env.example            ← Template for .env
│   └── requirements.txt        ← Python dependencies
│
├── frontend/                   ← Angular frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/           ← Auth, Guards, Interceptors
│   │   │   ├── shared/         ← Reusable components
│   │   │   ├── features/       ← Feature modules (dashboard, bugs, etc.)
│   │   │   └── layout/         ← Sidebar and topbar
│   │   └── environments/       ← Environment configs
│   └── package.json
│
├── .github/workflows/          ← GitHub Actions CI/CD
├── docker-compose.yml          ← Local development with Docker
└── README.md
```

---

## 🔧 Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment with Python 3.13
py -3.13 -m venv venv

# 3. Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
copy .env.example .env
# Edit .env with your PostgreSQL credentials

# 6. Create the PostgreSQL database
# In psql: CREATE DATABASE ai_testing_platform;

# 7. Run database migrations (Phase 2)
alembic upgrade head

# 8. Start the backend server
uvicorn app.main:app --reload --port 8000
```

The backend will be available at:
- **API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

---

## 🎨 Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies (already done by ng new)
npm install

# 3. Install Angular Material
ng add @angular/material

# 4. Start the development server
ng serve --open
```

The frontend will be available at: **http://localhost:4200**

---

## 🗄️ Database Setup

1. Install PostgreSQL 14+
2. Create the database:
   ```sql
   CREATE DATABASE ai_testing_platform;
   ```
3. Update `DATABASE_URL` in `backend/.env`
4. Run migrations: `alembic upgrade head`

---

## 🧪 Running Tests

### Backend Tests
```bash
cd backend
.\venv\Scripts\activate   # Windows
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
ng test
```

---

## 🛠️ Development Phases

- [x] Phase 0: Planning & Architecture
- [x] Phase 1: Project Setup
- [X] Phase 2: Authentication & Database
- [ ] Phase 3: Organization & Projects
- [ ] Phase 4: Requirements
- [ ] Phase 5: Test Cases & Suites
- [ ] Phase 6: Test Plans & Execution
- [ ] Phase 7: Bug Management
- [ ] Phase 8: Dashboard & Reports
- [ ] Phase 9: AI Integration
- [ ] Phase 10: Playwright Integration
- [ ] Phase 11: Production Deployment

🏛️ System Architecture
┌────────────────────────────────────────────────────────────────────────┐
│                        ANGULAR 17 CLIENT                               │
│   (Standalone Components, Material Design, Chart.js, JWT Interceptor)  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTPS / REST (JSON)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ API Endpoints (v1)                                               │  │
│  │ /auth · /organizations · /projects · /requirements · /test-cases │  │
│  │ /test-runs · /bugs · /analytics                                  │  │
│  └───────────────────────────────┬──────────────────────────────────┘  │
│                                  │                                     │
│  ┌───────────────────────────────▼──────────────────────────────────┐  │
│  │ Business Logic & Security Services (JWT, Multi-Tenant Guard)     │  │
│  └───────────────────────────────┬──────────────────────────────────┘  │
│                                  │                                     │
│  ┌───────────────────────────────▼──────────────────────────────────┐  │
│  │ Data Access Layer (SQLAlchemy ORM + Repository Pattern)          │  │
│  └───────────────────────────────┬──────────────────────────────────┘  │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │ SQL (psycopg3)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        POSTGRESQL DATABASE                             │
│   (Tenants · Users · Reqs · Test Cases · Runs · Bugs · Audits)         │
└────────────────────────────────────────────────────────────────────────┘


✨ Key Platform Features
Multi-Tenant Workspaces (Phase 3): Isolated organization workspaces, role-based access control (Admin, Member, Superadmin), and project management.
Requirements Management & PRD Ingestion (Phase 4): Upload product specifications (.pdf, .md, .txt) with document parsing and acceptance criteria tracking.
Test Case Authoring & Suites (Phase 5): Multi-step procedural testing with preconditions, test data, expected results, priorities, and requirement traceability.
Test Execution Worksheets (Phase 6): Group test cases into execution runs by environment (Local, Staging, QA, Production). Split-screen live runner with single-click Pass/Fail/Blocked/Skip logging.
Bug Tracker & Defect Management (Phase 7): 1-click defect reporting from failed execution steps. Full lifecycle management (Open 
→
→ In Progress 
→
→ Resolved 
→
→ Closed) with bidirectional requirement linking.
Executive Analytics & Reporting (Phase 8): Health scoring algorithm (0–100), pass/fail velocity bar charts, bug severity doughnut charts, requirement coverage rings, and one-click CSV report exports.

🛠️ Technology Stack
Layer	Technologies
Frontend	Angular 17, TypeScript, Angular Material, Chart.js, SCSS
Backend	FastAPI, Python 3.13, Pydantic v2, Uvicorn
Database	PostgreSQL, SQLAlchemy 2.0 ORM, Alembic Migrations
Authentication	JWT (OAuth2 Password Bearer), Passlib (Bcrypt)
Testing	Pytest, Pytest-Asyncio, HTTPX (52 automated integration tests)


🚀 Local Quickstart Guide
1. Prerequisites
Python 3.11 – 3.13
Node.js 18+ and npm 9+
PostgreSQL 14+

Roadmap & Upcoming Milestones
 Phase 1–2: Monorepo Architecture, JWT Auth, Database Schema
 Phase 3: Multi-Tenant Organizations & Projects
 Phase 4: Requirements Ingestion & PRD Parser
 Phase 5: Test Cases & Suites Procedural Authoring
 Phase 6: Test Execution Worksheets & Interactive Runner
 Phase 7: Bug Tracker & Defect Lifecycle Management
 Phase 8: Executive Analytics Dashboard & CSV Exports
 Phase 9: AI Test Case Synthesis & Root-Cause Intelligence (LLM)
 Phase 10: Playwright Autonomous Browser Automation
 Phase 11: Production Dockerization, CI/CD, & Cloud Deployment
 