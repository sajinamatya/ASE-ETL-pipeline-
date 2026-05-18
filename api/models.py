from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class Employee(Base):
    __tablename__ = "employee"
    
    employee_id = Column(String(100), primary_key=True, index=True)
    department_id = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    job_code = Column(String(100))
    hire_date = Column(Date)
    
class Timesheet(Base):
    __tablename__ = "timesheet"
    
    timesheet_id = Column(Integer, primary_key=True, index=True)
    department_id = Column(String(100))
    employee_id = Column(String(100))
    hours_worked = Column(Numeric)
    punch_apply_date = Column(Date)