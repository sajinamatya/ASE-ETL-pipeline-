"""
models.py — SQLAlchemy ORM models AND Pydantic schemas in one place.

ORM Models:  User, Employee, Timesheet
Pydantic:    Token, TokenData, UserCreate, UserOut,
             EmployeeBase, EmployeeCreate, EmployeeUpdate, EmployeeOut,
             TimesheetOut, EmployeeListResponse, TimesheetListResponse
"""

from datetime import date, datetime
from typing import Optional

# ── SQLAlchemy ────────────────────────────────────────────────────────
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ── Pydantic ──────────────────────────────────────────────────────────
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from api.database import Base


# ═════════════════════════════════════════════════════════════════════
#  SQLAlchemy ORM Models
# ═════════════════════════════════════════════════════════════════════

class User(Base):
    """Application users who authenticate via the API."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False)
    # role values: "admin" → full CRUD on employees | "viewer" → read-only
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Employee(Base):
    """Core employee record."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    date_joined: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    timesheets: Mapped[list["Timesheet"]] = relationship("Timesheet", back_populates="employee")


class Timesheet(Base):
    """Daily timesheet entry linked to an employee."""

    __tablename__ = "timesheets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hours_worked: Mapped[float] = mapped_column(Float, nullable=False)
    project: Mapped[str] = mapped_column(String(200), nullable=True)
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped["Employee"] = relationship("Employee", back_populates="timesheets")


# ═════════════════════════════════════════════════════════════════════
#  Pydantic Schemas
# ═════════════════════════════════════════════════════════════════════

# ── Auth ──────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ── User ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(default="viewer", pattern="^(admin|viewer)$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


# ── Employee ──────────────────────────────────────────────────────────

class EmployeeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, examples=["Jane Doe"])
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=100, examples=["Engineering"])
    role: str = Field(..., min_length=1, max_length=100, examples=["Software Engineer"])
    date_joined: date


class EmployeeCreate(EmployeeBase):
    """Payload for POST /employees"""
    pass


class EmployeeUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    date_joined: Optional[date] = None


class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ── Timesheet ─────────────────────────────────────────────────────────

class TimesheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    work_date: date
    hours_worked: float
    project: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


# ── Paginated list wrappers ────────────────────────────────────────────

class EmployeeListResponse(BaseModel):
    total: int
    items: list[EmployeeOut]


class TimesheetListResponse(BaseModel):
    total: int
    items: list[TimesheetOut]
