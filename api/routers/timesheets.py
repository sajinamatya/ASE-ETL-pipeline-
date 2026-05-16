"""
Timesheet router — read-only access.

All endpoints require authentication (any role).
Admins and viewers both have read access; no write operations are exposed.

Endpoints:
  GET /timesheets                   → list all, filterable by employee / date range
  GET /timesheets/{id}              → single timesheet entry
  GET /timesheets/employee/{emp_id} → all entries for one employee
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api import models
from api.auth import get_current_user
from api.database import get_db

router = APIRouter(prefix="/timesheets", tags=["Timesheets"])


@router.get(
    "",
    response_model=models.TimesheetListResponse,
    summary="List timesheets — filterable by employee and/or date range",
)
def list_timesheets(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    date_from: Optional[date] = Query(None, description="Start date (inclusive), YYYY-MM-DD"),
    date_to: Optional[date] = Query(None, description="End date (inclusive), YYYY-MM-DD"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be earlier than or equal to date_to.",
        )

    query = db.query(models.Timesheet)

    if employee_id is not None:
        # Verify the employee exists
        if not db.get(models.Employee, employee_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with id={employee_id} not found.",
            )
        query = query.filter(models.Timesheet.employee_id == employee_id)

    if date_from:
        query = query.filter(models.Timesheet.work_date >= date_from)
    if date_to:
        query = query.filter(models.Timesheet.work_date <= date_to)

    total = query.count()
    items = (
        query.order_by(models.Timesheet.work_date.desc(), models.Timesheet.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return models.TimesheetListResponse(total=total, items=items)


@router.get(
    "/employee/{employee_id}",
    response_model=models.TimesheetListResponse,
    summary="List all timesheet entries for a specific employee",
)
def list_timesheets_by_employee(
    employee_id: int,
    date_from: Optional[date] = Query(None, description="Start date (inclusive)"),
    date_to: Optional[date] = Query(None, description="End date (inclusive)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    if not db.get(models.Employee, employee_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found.",
        )

    query = db.query(models.Timesheet).filter(models.Timesheet.employee_id == employee_id)

    if date_from:
        query = query.filter(models.Timesheet.work_date >= date_from)
    if date_to:
        query = query.filter(models.Timesheet.work_date <= date_to)

    total = query.count()
    items = (
        query.order_by(models.Timesheet.work_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return models.TimesheetListResponse(total=total, items=items)


@router.get(
    "/{timesheet_id}",
    response_model=models.TimesheetOut,
    summary="Retrieve a single timesheet entry by ID",
)
def get_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    entry = db.get(models.Timesheet, timesheet_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timesheet entry with id={timesheet_id} not found.",
        )
    return entry
