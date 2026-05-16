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
                hashed_password=hash_password("Admin@12345"),
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

        db.flush()  # get IDs before adding timesheets

        # ── 3. Sample employees ───────────────────────────────────────
        sample_employees = [
            {
                "name": "Alice Sharma",
                "email": "alice.sharma@company.com",
                "department": "Engineering",
                "role": "Software Engineer",
                "date_joined": date(2022, 3, 15),
            },
            {
                "name": "Bob Karki",
                "email": "bob.karki@company.com",
                "department": "Data",
                "role": "Data Analyst",
                "date_joined": date(2021, 7, 1),
            },
            {
                "name": "Clara Rai",
                "email": "clara.rai@company.com",
                "department": "HR",
                "role": "HR Manager",
                "date_joined": date(2020, 11, 20),
            },
        ]

        created_employees = []
        for emp_data in sample_employees:
            existing = (
                db.query(models.Employee)
                .filter(models.Employee.email == emp_data["email"])
                .first()
            )
            if not existing:
                emp = models.Employee(**emp_data)
                db.add(emp)
                db.flush()
                created_employees.append(emp)
                print(f"✓  Created employee: {emp_data['name']}")
            else:
                created_employees.append(existing)
                print(f"–  Employee '{emp_data['name']}' already exists, skipping.")

        # ── 4. Sample timesheets ──────────────────────────────────────
        sample_timesheets = [
            {"employee": created_employees[0], "work_date": date(2024, 5, 1),  "hours_worked": 8.0, "project": "ETL Pipeline v2",   "notes": "Implemented extract module"},
            {"employee": created_employees[0], "work_date": date(2024, 5, 2),  "hours_worked": 7.5, "project": "ETL Pipeline v2",   "notes": "Unit tests for transform"},
            {"employee": created_employees[1], "work_date": date(2024, 5, 1),  "hours_worked": 6.0, "project": "Dashboard",          "notes": "Built sales KPI charts"},
            {"employee": created_employees[1], "work_date": date(2024, 5, 3),  "hours_worked": 8.0, "project": "Dashboard",          "notes": "Connected to live DB"},
            {"employee": created_employees[2], "work_date": date(2024, 5, 2),  "hours_worked": 5.0, "project": "Onboarding Process", "notes": "Updated policy documents"},
        ]

        for ts_data in sample_timesheets:
            emp = ts_data.pop("employee")
            existing = (
                db.query(models.Timesheet)
                .filter(
                    models.Timesheet.employee_id == emp.id,
                    models.Timesheet.work_date == ts_data["work_date"],
                )
                .first()
            )
            if not existing:
                ts = models.Timesheet(employee_id=emp.id, **ts_data)
                db.add(ts)
                print(f"✓  Added timesheet for employee_id={emp.id} on {ts_data['work_date']}")
            else:
                print(f"–  Timesheet for employee_id={emp.id} on {ts_data['work_date']} exists, skipping.")

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
