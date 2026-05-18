"""
schemas.py — DEPRECATED.

All Pydantic schemas have been merged into api/models.py
(which now holds both SQLAlchemy ORM models and Pydantic schemas).

This file is kept only to avoid import errors in any external tooling.
Import from api.models directly.
"""

from api.models import (  # noqa: F401  re-export for backward compat
    Token,
    TokenData,
    UserCreate,
    UserOut,
    EmployeeBase,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeOut,
    TimesheetOut,
    EmployeeListResponse,
    TimesheetListResponse,
)
