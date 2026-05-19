import os
import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Runs automated post-load quality control and validation scripts on the database.
    Checks for referential integrity, null constraints, and anomaly detection.
    """
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def run_all_checks(self):
        logger.info("Starting automated Data Quality Validation Checks...")
        
        validations = [
            self.check_fact_orphans,
            self.check_negative_hours,
            self.check_future_punch_dates,
            self.check_null_keys_in_dimensions
        ]
        
        failed_checks = 0
        for check in validations:
            try:
                check()
            except AssertionError as ae:
                logger.error(f"Validation Failed: {ae}")
                failed_checks += 1
            except Exception as e:
                logger.error(f"Error executing validation script: {e}", exc_info=True)
                failed_checks += 1
                
        if failed_checks > 0:
            raise ValueError(f"Data Quality Validation failed for {failed_checks} checks. Check logs for details.")
        logger.info("All Data Quality Validation checks passed successfully!")

    def check_fact_orphans(self):
        """Check if any facts in the timesheet highlight missing employees in the dimension table."""
        query = "SELECT COUNT(*) FROM fact_timesheet WHERE dim_employee_key NOT IN (SELECT dim_employee_key FROM dim_employee)"
        with self.engine.connect() as conn:
            orphan_count = conn.execute(text(query)).scalar()
            assert orphan_count == 0, f"Referential Integrity Error: Found {orphan_count} orphaned records in fact_timesheet."

    def check_negative_hours(self):
        """Ensure no timesheet records exist with negative working hours."""
        query = "SELECT COUNT(*) FROM fact_timesheet WHERE hours_worked < 0"
        with self.engine.connect() as conn:
            negative_count = conn.execute(text(query)).scalar()
            assert negative_count == 0, f"Data Anomaly: Found {negative_count} timesheet records with negative hours."

    def check_future_punch_dates(self):
        """Ensure no punch apply dates are strictly in the future."""
        query = "SELECT COUNT(*) FROM fact_timesheet WHERE dim_date_key > CURRENT_DATE + INTERVAL '1 day'"
        with self.engine.connect() as conn:
            future_count = conn.execute(text(query)).scalar()
            assert future_count == 0, f"Data Anomaly: Found {future_count} timesheets with dates in the future."

    def check_null_keys_in_dimensions(self):
        """Check that no dimension tables contain NULL primary keys."""
        with self.engine.connect() as conn:
            emp_nulls = conn.execute(text("SELECT COUNT(*) FROM dim_employee WHERE dim_employee_key IS NULL")).scalar()
            assert emp_nulls == 0, "Null Constraint Violation: NULL dim_employee_key found in dim_employee."
            
