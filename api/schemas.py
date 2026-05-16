"""
Pydantic v2 schemas for request validation and response serialisation.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ─────────────────────────────── Auth ────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ─────────────────────────────── User ────────────────────────────────

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


# ─────────────────────────────── Employee ────────────────────────────

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
    """All fields optional so callers can PATCH individual attributes."""
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


# ─────────────────────────────── Timesheet ───────────────────────────

class TimesheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    work_date: date
    hours_worked: float
    project: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class TimesheetListResponse(BaseModel):
    total: int
    items: list[TimesheetOut]


class EmployeeListResponse(BaseModel):
    total: int
    items: list[EmployeeOut]
