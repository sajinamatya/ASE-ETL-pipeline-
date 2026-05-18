from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str

class UserBase(BaseModel):
    username: str
    email: str
    role: str = "viewer"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class EmployeeBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department_id: Optional[str] = None
    job_code: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    employee_id: str
    hire_date: Optional[date] = None

class EmployeeUpdate(EmployeeBase):
    pass

class EmployeeResponse(EmployeeCreate):
    model_config = ConfigDict(from_attributes=True)

class TimesheetResponse(BaseModel):
    timesheet_id: int
    department_id: Optional[str] = None
    employee_id: Optional[str] = None
    hours_worked: Optional[float] = None
    punch_apply_date: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)