"""
Employee router — full CRUD operations.

Access control:
  GET    /employees        → any authenticated user
  GET    /employees/{id}   → any authenticated user
  POST   /employees        → admin only
  PUT    /employees/{id}   → admin only
  DELETE /employees/{id}   → admin only
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api import models
from api.auth import get_current_user, require_admin
from api.database import get_db

router = APIRouter(prefix="/employees", tags=["Employees"])


# ─────────────────────────── READ ────────────────────────────────────

@router.get(
    "",
    response_model=models.EmployeeListResponse,
    summary="List all employees",
)
def list_employees(
    department: Optional[str] = Query(None, description="Filter by department"),
    role: Optional[str] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    query = db.query(models.Employee)
    if department:
        query = query.filter(models.Employee.department.ilike(f"%{department}%"))
    if role:
        query = query.filter(models.Employee.role.ilike(f"%{role}%"))

    total = query.count()
    items = query.order_by(models.Employee.id).offset(skip).limit(limit).all()
    return models.EmployeeListResponse(total=total, items=items)


@router.get(
    "/{employee_id}",
    response_model=models.EmployeeOut,
    summary="Retrieve an employee by ID",
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found.",
        )
    return employee


# ─────────────────────────── CREATE ──────────────────────────────────

@router.post(
    "",
    response_model=models.EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new employee (admin only)",
)
def create_employee(
    payload: models.EmployeeCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    # Email uniqueness check
    if db.query(models.Employee).filter(models.Employee.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee with email '{payload.email}' already exists.",
        )
    employee = models.Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


# ─────────────────────────── UPDATE ──────────────────────────────────

@router.put(
    "/{employee_id}",
    response_model=models.EmployeeOut,
    summary="Update an employee's details (admin only)",
)
def update_employee(
    employee_id: int,
    payload: models.EmployeeUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found.",
        )

    # Only apply fields that were explicitly provided
    update_data = payload.model_dump(exclude_unset=True)

    # Check email uniqueness if it's being changed
    if "email" in update_data and update_data["email"] != employee.email:
        if db.query(models.Employee).filter(models.Employee.email == update_data["email"]).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{update_data['email']}' is already in use.",
            )

    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


# ─────────────────────────── DELETE ──────────────────────────────────

@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an employee (admin only)",
)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found.",
        )
    db.delete(employee)
    db.commit()
