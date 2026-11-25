"""
app/models/__init__.py
───────────────────────
PURPOSE:
  This file makes the 'models' directory a Python package.
  More importantly, it re-exports all models from one place.

WHY RE-EXPORT HERE?
  Instead of writing in every file:
      from app.models.user import User
      from app.models.project import Project   (future phase)

  You can write:
      from app.models import User

  Also, Alembic needs to import ALL models in one place so it can
  detect which tables to create/modify during migrations.
  When we add more models (Project, Bug, TestCase...) in later phases,
  we just add their imports here.
"""

from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationMember, OrgRole  # Phase 3
from app.models.project import Project, ProjectStatus                           # Phase 3
from app.models.requirement import (                                            # Phase 4
    RequirementDocument,
    Requirement,
    AcceptanceCriteria,
    DocParsingStatus,
    RequirementCategory,
    RequirementPriority,
    RequirementStatus,
)
from app.models.test_case import (                                              # Phase 5
    TestSuite,
    TestCase,
    TestStep,
    TestType,
    TestPriority,
    TestStatus,
)
from app.models.test_run import (                                               # Phase 6
    TestRun,
    TestRunItem,
    RunStatus,
    RunEnvironment,
    RunResult,
)
from app.models.bug import (                                                    # Phase 7
    Bug,
    BugSeverity,
    BugPriority,
    BugStatus,
)

# __all__ controls what gets exported when someone writes: from app.models import *
__all__ = [
    "User",
    "UserRole",
    "Organization",
    "OrganizationMember",
    "OrgRole",
    "Project",
    "ProjectStatus",
    "RequirementDocument",
    "Requirement",
    "AcceptanceCriteria",
    "DocParsingStatus",
    "RequirementCategory",
    "RequirementPriority",
    "RequirementStatus",
    "TestSuite",
    "TestCase",
    "TestStep",
    "TestType",
    "TestPriority",
    "TestStatus",
    "TestRun",
    "TestRunItem",
    "RunStatus",
    "RunEnvironment",
    "RunResult",
    "Bug",
    "BugSeverity",
    "BugPriority",
    "BugStatus",
]

