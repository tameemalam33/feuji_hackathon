"""
SaaS Models for AutoQA Pro
Defines data models for multi-user features, projects, tasks, and reports
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from uuid import UUID
import json


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    TESTER = "tester"
    DEVELOPER = "developer"


class ProjectMemberRole(str, Enum):
    """Roles for project members"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class TaskStatus(str, Enum):
    """Status values for QA tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Priority levels for tasks"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BugSeverity(str, Enum):
    """Severity levels for bugs"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BugStatus(str, Enum):
    """Status values for bug reports"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "won_t_fix"


class ReportFileType(str, Enum):
    """Types of report files"""
    CSV = "csv"
    PDF = "pdf"
    SCREENSHOT = "screenshot"
    LOG = "log"


@dataclass
class SaasUser:
    """User model"""
    id: UUID
    email: str
    username: Optional[str]
    full_name: Optional[str]
    password_hash: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self, include_password=False):
        """Convert to dictionary"""
        data = {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_password:
            data["password_hash"] = self.password_hash
        return data


@dataclass
class SaasProject:
    """Project model"""
    id: UUID
    name: str
    description: Optional[str]
    base_url: str
    owner_id: UUID
    is_public: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "base_url": self.base_url,
            "owner_id": str(self.owner_id),
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class SaasProjectMember:
    """Project member model"""
    id: UUID
    project_id: UUID
    user_id: UUID
    role: ProjectMemberRole
    created_at: datetime

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "user_id": str(self.user_id),
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SaasQaTask:
    """QA task model"""
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    created_by: UUID
    assigned_to: Optional[UUID]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "title": self.title,
            "description": self.description,
            "created_by": str(self.created_by),
            "assigned_to": str(self.assigned_to) if self.assigned_to else None,
            "status": self.status.value,
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class SaasBug:
    """Bug report model"""
    id: UUID
    task_id: Optional[UUID]
    project_id: UUID
    title: str
    description: Optional[str]
    severity: BugSeverity
    status: BugStatus
    reported_by: Optional[UUID]
    assigned_to: Optional[UUID]
    screenshot_url: Optional[str]
    page_url: Optional[str]
    error_message: Optional[str]
    steps_to_reproduce: Optional[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id) if self.task_id else None,
            "project_id": str(self.project_id),
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "reported_by": str(self.reported_by) if self.reported_by else None,
            "assigned_to": str(self.assigned_to) if self.assigned_to else None,
            "screenshot_url": self.screenshot_url,
            "page_url": self.page_url,
            "error_message": self.error_message,
            "steps_to_reproduce": self.steps_to_reproduce,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class SaasReport:
    """Test report model"""
    id: UUID
    project_id: UUID
    task_id: Optional[UUID]
    title: str
    sqlite_run_id: Optional[int]
    sqlite_batch_id: Optional[str]
    report_json: Optional[dict]
    total_tests: Optional[int]
    passed_tests: Optional[int]
    failed_tests: Optional[int]
    success_rate: Optional[float]
    test_duration_ms: Optional[int]
    generated_at: datetime
    created_at: datetime

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "title": self.title,
            "sqlite_run_id": self.sqlite_run_id,
            "sqlite_batch_id": self.sqlite_batch_id,
            "report_json": self.report_json,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": self.success_rate,
            "test_duration_ms": self.test_duration_ms,
            "generated_at": self.generated_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SaasReportFile:
    """Report file model"""
    id: UUID
    report_id: UUID
    file_type: ReportFileType
    file_path: str
    file_name: str
    file_size_bytes: Optional[int]
    created_at: datetime

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "report_id": str(self.report_id),
            "file_type": self.file_type.value,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size_bytes": self.file_size_bytes,
            "created_at": self.created_at.isoformat(),
        }
