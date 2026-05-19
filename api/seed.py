"""
Bootstrap script — creates the first admin user and sample data.

Usage (from the project root):
    python -m api.seed

Environment variables are read from .env automatically.
Re-running is safe: existing records are skipped.
"""

import sys
from datetime import date

from api.database import SessionLocal, engine
from api import models
from api.auth import hash_password


def seed():
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ── 1. Admin user ────────────────────────────────────────────
        if not db.query(models.User).filter(models.User.username == "admin").first():
            admin = models.User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("admin"),
                role="admin",
            )
            db.add(admin)
            print("✓  Created admin user  (username: admin / password: Admin@12345)")
        else:
            print("–  Admin user already exists, skipping.")

        # ── 2. Viewer user ───────────────────────────────────────────
        if not db.query(models.User).filter(models.User.username == "viewer").first():
            viewer = models.User(
                username="viewer",
                email="viewer@example.com",
                hashed_password=hash_password("Viewer@12345"),
                role="viewer",
            )
            db.add(viewer)
            print("✓  Created viewer user (username: viewer / password: Viewer@12345)")
        else:
            print("–  Viewer user already exists, skipping.")

        db.commit() # Save users immediately before proceeding
        db.flush()  # get IDs before adding timesheets

        # ── 3. Sample employees ───────────────────────────────────────
        sample_employees = [
            {
                "employee_id": "EMP001",
                "department_id": "DEP001",
                "first_name": "Alice",
                "last_name": "Sharma",
                "job_code": "ENG01",
                "hire_date": date(2022, 3, 15),
            },
            {
                "employee_id": "EMP002",
                "department_id": "DEP002",
                "first_name": "Bob",
                "last_name": "Karki",
                "job_code": "DAT01",
                "hire_date": date(2021, 7, 1),
            },
            {
                "employee_id": "EMP003",
                "department_id": "DEP003",
                "first_name": "Clara",
                "last_name": "Rai",
                "job_code": "HR01",
                "hire_date": date(2020, 11, 20),
            },
        ]

        created_employees = []
        for emp_data in sample_employees:
            existing = (
                db.query(models.Employee)
                .filter(models.Employee.employee_id == emp_data["employee_id"])
                .first()
            )
            if not existing:
                emp = models.Employee(**emp_data)
                db.add(emp)
                db.flush()
                created_employees.append(emp)
                print(f"✓  Created employee: {emp_data['first_name']} {emp_data['last_name']}")
            else:
                created_employees.append(existing)
                print(f"–  Employee '{emp_data['first_name']} {emp_data['last_name']}' already exists, skipping.")

        # ── 4. Sample timesheets ──────────────────────────────────────
        sample_timesheets = [
            {"employee_id": created_employees[0].employee_id, "department_id": created_employees[0].department_id, "punch_apply_date": date(2024, 5, 1),  "hours_worked": 8.0},
            {"employee_id": created_employees[0].employee_id, "department_id": created_employees[0].department_id, "punch_apply_date": date(2024, 5, 2),  "hours_worked": 7.5},
            {"employee_id": created_employees[1].employee_id, "department_id": created_employees[1].department_id, "punch_apply_date": date(2024, 5, 1),  "hours_worked": 6.0},
            {"employee_id": created_employees[1].employee_id, "department_id": created_employees[1].department_id, "punch_apply_date": date(2024, 5, 3),  "hours_worked": 8.0},
            {"employee_id": created_employees[2].employee_id, "department_id": created_employees[2].department_id, "punch_apply_date": date(2024, 5, 2),  "hours_worked": 5.0},
        ]

        for ts_data in sample_timesheets:
            existing = (
                db.query(models.Timesheet)
                .filter(
                    models.Timesheet.employee_id == ts_data["employee_id"],
                    models.Timesheet.punch_apply_date == ts_data["punch_apply_date"],
                )
                .first()
            )
            if not existing:
                ts = models.Timesheet(**ts_data)
                db.add(ts)
                print(f"✓  Added timesheet for employee_id={ts_data['employee_id']} on {ts_data['punch_apply_date']}")
            else:
                print(f"–  Timesheet for employee_id={ts_data['employee_id']} on {ts_data['punch_apply_date']} exists, skipping.")

        db.commit()
        print("\n✅  Seeding complete.")

    except Exception as exc:
        db.rollback()
        print(f"\n❌  Seeding failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
