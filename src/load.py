import os
import io
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from minio import Minio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataLoader:
    """
    DataLoader is responsible for loading processed data into the PostgreSQL database.
    It supports reading the source data from local files or directly from MinIO (S3-compatible storage).
    """
    def __init__(self, db_url: str, minio_endpoint: str = None, minio_access_key: str = None, minio_secret_key: str = None):
        self.engine = create_engine(db_url)
        self.minio_client = None
        
        # Initialize MinIO client if credentials are provided
        if minio_endpoint and minio_access_key and minio_secret_key:
            self.minio_client = Minio(
                minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=False  # Set to True if using HTTPS
            )

    def load_from_local(self, file_path: str, table_name: str, file_type: str = 'parquet'):
        """Reads data from a local file and loads it into the database."""
        if not os.path.exists(file_path):
            logger.error(f"Local file not found: {file_path}")
            raise FileNotFoundError(f"Local file not found: {file_path}")
            
        logger.info(f"Reading from local file: {file_path}")
        try:
            if file_type == 'parquet':
                df = pd.read_parquet(file_path)
            elif file_type == 'csv':
                df = pd.read_csv(file_path, low_memory=False)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
                
            self._load_dataframe_to_db(df, table_name)
        except Exception as e:
            logger.error(f"Failed to load data from {file_path} into {table_name}: {e}", exc_info=True)
            raise

    def load_from_minio(self, bucket_name: str, object_name: str, table_name: str, file_type: str = 'parquet'):
        """Reads data from a MinIO bucket and loads it into the database."""
        if not self.minio_client:
            logger.error("MinIO client is not initialized.")
            raise ValueError("MinIO client is not initialized. Please provide MinIO credentials during DataLoader initialization.")
            
        logger.info(f"Reading from MinIO - Bucket: {bucket_name}, Object: {object_name}")
        try:
            response = self.minio_client.get_object(bucket_name, object_name)
            
            try:
                file_data = io.BytesIO(response.read())
                if file_type == 'parquet':
                    df = pd.read_parquet(file_data)
                elif file_type == 'csv':
                    df = pd.read_csv(file_data, low_memory=False)
                else:
                    raise ValueError(f"Unsupported file type: {file_type}")
            finally:
                response.close()
                response.release_conn()
                
            self._load_dataframe_to_db(df, table_name)
        except Exception as e:
            logger.error(f"Failed to load data from MinIO bucket {bucket_name} object {object_name}: {e}", exc_info=True)
            raise

    def _load_dataframe_to_db(self, df: pd.DataFrame, table_name: str):
        """Helper method to insert the DataFrame into PostgreSQL."""
        logger.info(f"Loading {len(df)} rows into table '{table_name}'...")
        # 'append' will add to the existing data; 'replace' would drop and recreate
        df.to_sql(table_name, self.engine, if_exists='append', index=False)
        logger.info(f"Successfully loaded data into '{table_name}'.")

    def load_normalized_data(self, employee_df: pd.DataFrame, timesheet_df: pd.DataFrame):
        """
        Splits and inserts the extracted data into normalized tables based on the ERD.
        Must insert in the order of foreign-key dependencies.
        """
        # 1. Organization
        org_df = employee_df[['organization_id']].drop_duplicates().dropna(subset=['organization_id'])
        # Add a dummy organization_name if missing in source or map appropriately
        if 'organization_name' not in org_df.columns:
            org_df['organization_name'] = 'Org_' + org_df['organization_id'].astype(str)
        self._load_dataframe_to_db(org_df, 'organization')

        # 2. Department
        dept_df = employee_df[['department_id', 'organization_id']].drop_duplicates().dropna(subset=['department_id'])
        if 'department_name' not in dept_df.columns:
            dept_df['department_name'] = 'Dept_' + dept_df['department_id'].astype(str)
        self._load_dataframe_to_db(dept_df, 'department')

        # 3. Manager
        manager_df = employee_df[['manager_employee_id', 'department_id', 'organization_id']].rename(
            columns={'manager_employee_id': 'manager_id'}
        ).drop_duplicates().dropna(subset=['manager_id'])
        if 'manager_employee_name' in employee_df.columns:
            manager_names = employee_df[['manager_employee_id', 'manager_employee_name']].rename(
                columns={'manager_employee_id': 'manager_id', 'manager_employee_name': 'manager_name'}
            ).drop_duplicates()
            manager_df = manager_df.merge(manager_names, on='manager_id', how='left')
        self._load_dataframe_to_db(manager_df, 'manager')

        # 4. Employee Job
        job_df = employee_df[['job_code']].drop_duplicates().dropna(subset=['job_code'])
        if 'job_title' not in job_df.columns:
            job_df['job_title'] = 'Job_' + job_df['job_code'].astype(str)
        if 'clinical_level' not in job_df.columns:
            job_df['clinical_level'] = None
        self._load_dataframe_to_db(job_df, 'employee_job')

        # 5. Employee
        emp_cols = [
            'department_id', 'first_name', 'middle_name', 'last_name', 'preferred_name',
            'job_code', 'job_start_date', 'organization_id', 'dob',
            'hire_date', 'recent_hire_date', 'anniversary_date', 'termination_date', 'years_of_experience',
            'work_email', 'address', 'city', 'state', 'zip_code', 'country', 'fte_status',
            'is_per_diem', 'cell_phone', 'work_phone', 'scheduled_weekly_hours', 'active_status', 'termination_reason'
        ]
        # Rename client_employee_id to employee_id if needed
        emp_base = employee_df.rename(columns={'client_employee_id': 'employee_id', 'manager_employee_id': 'manager_id'})
        existing_emp_cols = ['employee_id', 'manager_id'] + [c for c in emp_cols if c in emp_base.columns]
        emp_final_df = emp_base[existing_emp_cols].drop_duplicates(subset=['employee_id']).dropna(subset=['employee_id'])
        self._load_dataframe_to_db(emp_final_df, 'employee')

        # 6. Timesheet
        if timesheet_df is not None and not timesheet_df.empty:
            ts_cols = [
                'timesheet_id', 'department_id', 'home_department_id', 'client_employee_id',
                'pay_code', 'punch_in_comment', 'punch_out_comment', 'hours_worked',
                'punch_apply_date', 'punch_in_datetime', 'punch_out_datetime'
            ]
            ts_base = timesheet_df.rename(columns={'client_employee_id': 'employee_id'})
            existing_ts_cols = [c for c in ts_cols if c in ts_base.columns or c == 'employee_id']
            ts_final_df = ts_base[existing_ts_cols].drop_duplicates()
            self._load_dataframe_to_db(ts_final_df, 'timesheet')

        # 7. Schedule
        if timesheet_df is not None and 'scheduled_id' in timesheet_df.columns:
            sched_cols = ['scheduled_id', 'timesheet_id', 'scheduled_start_datetime', 'scheduled_end_datetime']
            existing_sched_cols = [c for c in sched_cols if c in timesheet_df.columns]
            sched_final_df = timesheet_df[existing_sched_cols].drop_duplicates().dropna(subset=['scheduled_id'])
            self._load_dataframe_to_db(sched_final_df, 'schedule')

    def execute_sql_script(self, script_path: str):
        """
        Reads and executes a SQL script. Used for creating dimensional models 
        or running specific transform logic post-load inside the database.
        """
        if not os.path.exists(script_path):
            logger.error(f"SQL Script not found: {script_path}")
            raise FileNotFoundError(f"SQL script not found: {script_path}")
            
        logger.info(f"Executing SQL script: {script_path}")
        try:
            with open(script_path, 'r', encoding='utf-8') as file:
                sql_string = file.read()
                
            with self.engine.begin() as conn:
                conn.execute(text(sql_string))
            logger.info(f"Successfully executed SQL script: {script_path}")
        except Exception as e:
            logger.error(f"Error executing SQL script {script_path}: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    # Example usage
    DB_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/etl_db")
    loader = DataLoader(db_url=DB_URL)
    
    # Assuming 'extracted_employee.parquet' exists locally
    # loader.load_from_local('data/processed/extracted_employee.parquet', 'employee')

