from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import logging

from api import models, schemas
from api.database import get_db
from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/timesheets",
    tags=["Timesheets"],
    dependencies=[Depends(get_current_user)] # Every route here requires authentication
)

@router.get("/", response_model=List[schemas.TimesheetResponse])
def read_timesheets(
    skip: int = 0, 
    limit: int = 100, 
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    List all timesheets. 
    Can be filtered by date range or specific employee.
    (Read-only access available to everyone).
    """
    logger.info(f"Fetching timesheets (skip={skip}, limit={limit}, employee_id={employee_id})")
    try:
        query = db.query(models.Timesheet)
        
        if employee_id:
            query = query.filter(models.Timesheet.employee_id == employee_id)
        if start_date:
            query = query.filter(models.Timesheet.punch_apply_date >= start_date)
        if end_date:
            query = query.filter(models.Timesheet.punch_apply_date <= end_date)
            
        return query.offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Error fetching timesheets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{timesheet_id}", response_model=schemas.TimesheetResponse)
def read_timesheet(timesheet_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific timesheet by ID."""
    logger.info(f"Fetching timesheet ID: {timesheet_id}")
    try:
        timesheet = db.query(models.Timesheet).filter(models.Timesheet.timesheet_id == timesheet_id).first()
        if not timesheet:
            logger.error(f"Timesheet ID {timesheet_id} not found.")
            raise HTTPException(status_code=404, detail="Timesheet not found")
        return timesheet
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timesheet {timesheet_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")