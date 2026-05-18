from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from api import models, schemas
from api.database import get_db
from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
    dependencies=[Depends(get_current_user)] # Basic auth barrier
)

def verify_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        logger.warning(f"Access denied for user {current_user.username}: Admin role required.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges."
        )

@router.get("/", response_model=List[schemas.EmployeeResponse])
def read_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all employees (Read-only access available to everyone)."""
    logger.info(f"Fetching employees (skip={skip}, limit={limit})")
    try:
        employees = db.query(models.Employee).offset(skip).limit(limit).all()
        return employees
    except Exception as e:
        logger.error(f"Error fetching employees: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{employee_id}", response_model=schemas.EmployeeResponse)
def read_employee(employee_id: str, db: Session = Depends(get_db)):
    """Get a specific employee by ID."""
    logger.info(f"Fetching employee ID: {employee_id}")
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if employee is None:
        logger.error(f"Employee ID {employee_id} not found.")
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@router.post("/", response_model=schemas.EmployeeResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin)])
def create_employee(employee: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    """Add a new employee (Admin only)."""
    logger.info(f"Attempting to create employee: {employee.employee_id}")
    target = db.query(models.Employee).filter(models.Employee.employee_id == employee.employee_id).first()
    if target:
        logger.warning(f"Employee ID {employee.employee_id} already exists.")
        raise HTTPException(status_code=400, detail="Employee ID already registered")
        
    try:
        db_employee = models.Employee(**employee.model_dump())
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        logger.info(f"Successfully created employee: {employee.employee_id}")
        return db_employee
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create employee {employee.employee_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during employee creation.")

@router.put("/{employee_id}", response_model=schemas.EmployeeResponse, dependencies=[Depends(verify_admin)])
def update_employee(employee_id: str, payload: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    """Update an existing employee (Admin only)."""
    logger.info(f"Attempting to update employee ID: {employee_id}")
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not employee:
        logger.error(f"Employee ID {employee_id} not found for update.")
        raise HTTPException(status_code=404, detail="Employee not found")
        
    try:
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(employee, key, value)
            
        db.commit()
        db.refresh(employee)
        logger.info(f"Successfully updated employee: {employee_id}")
        return employee
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update employee {employee_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during employee update.")

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin)])
def delete_employee(employee_id: str, db: Session = Depends(get_db)):
    """Delete an employee and all associated timesheets (Admin only)."""
    logger.info(f"Attempting to delete employee ID: {employee_id}")
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not employee:
        logger.error(f"Employee ID {employee_id} not found for deletion.")
        raise HTTPException(status_code=404, detail="Employee not found")
        
    try:
        db.delete(employee)
        db.commit()
        logger.info(f"Successfully deleted employee: {employee_id}")
        return {"ok": True}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete employee {employee_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during employee deletion.")