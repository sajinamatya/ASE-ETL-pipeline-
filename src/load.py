import os
import io
import logging
import pandas as pd
from sqlalchemy import create_engine, text
# pyrefly: ignore [missing-import]
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
        """Helper method to insert the DataFrame into PostgreSQL, avoiding duplicates."""
        if df.empty:
            logger.info(f"DataFrame for table '{table_name}' is empty. Skipping.")
            return

        from sqlalchemy import inspect
        try:
            inspector = inspect(self.engine)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = pk_constraint.get('constrained_columns', [])
        except Exception as e:
            logger.warning(f"Could not inspect table '{table_name}': {e}")
            pk_cols = []

        df_to_load = df
        if pk_cols and all(col in df.columns for col in pk_cols):
            try:
                pk_select = ", ".join([f'"{col}"' for col in pk_cols])
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT {pk_select} FROM {table_name}"))
                    existing_keys = {row[0] if len(pk_cols) == 1 else tuple(row) for row in result}
                
                if len(pk_cols) == 1:
                    pk_col = pk_cols[0]
                    existing_set = {str(k) for k in existing_keys}
                    df_to_load = df[~df[pk_col].astype(str).isin(existing_set)]
                else:
                    existing_set = {tuple(str(x) for x in k) if isinstance(k, tuple) else (str(k),) for k in existing_keys}
                    df_to_load = df[~df[pk_cols].apply(lambda r: tuple(str(x) for x in r), axis=1).isin(existing_set)]
                    
                logger.info(f"Table '{table_name}': filtered {len(df) - len(df_to_load)} existing rows, loading {len(df_to_load)} new rows.")
            except Exception as e:
                logger.warning(f"Error checking existing keys for table '{table_name}': {e}")
                df_to_load = df

        if df_to_load.empty:
            logger.info(f"All records for table '{table_name}' already exist in the database. Skipping insert.")
            return

        logger.info(f"Loading {len(df_to_load)} rows into table '{table_name}'...")
        df_to_load.to_sql(table_name, self.engine, if_exists='append', index=False)
        logger.info(f"Successfully loaded data into '{table_name}'.")

    def load_normalized_data(self, employee_df: pd.DataFrame, timesheet_df: pd.DataFrame = None):
        """
        Splits and inserts the extracted data into normalized tables based on the ERD.
        Must insert in the order of foreign-key dependencies.
        """
        if employee_df is None or employee_df.empty:
            logger.warning("Employee DataFrame is empty. Skipping normalized data load.")
            return

        # Clean null-like string representations in dataframes
        null_replacements = {'nan': None, 'NaN': None, '[NULL]': None, 'None': None, '': None, 'NAT': None, 'NaT': None}
        
        employee_df = employee_df.replace(null_replacements)
        if timesheet_df is not None and not timesheet_df.empty:
            timesheet_df = timesheet_df.replace(null_replacements)

        # Execute loads in dependency order
        self._load_organization(employee_df)
        self._load_department(employee_df, timesheet_df)
        self._load_manager(employee_df)
        self._load_employee_job(employee_df)
        self._load_employee(employee_df)
        
        if timesheet_df is not None and not timesheet_df.empty:
            self._load_timesheet(timesheet_df)
            self._load_schedule(timesheet_df)

    def _load_organization(self, employee_df: pd.DataFrame):
        """Extracts and loads organization data."""
        org_df = employee_df[['organization_id']].drop_duplicates().dropna(subset=['organization_id'])
        if 'organization_name' not in org_df.columns:
            org_df['organization_name'] = 'Org_' + org_df['organization_id'].astype(str)
        self._load_dataframe_to_db(org_df, 'organization')

    def _load_department(self, employee_df: pd.DataFrame, timesheet_df: pd.DataFrame):
        """Extracts and loads department data from all available sources."""
        dept_dfs = []
        if 'department_id' in employee_df.columns:
            emp_dept = employee_df[['department_id', 'organization_id']].rename(columns={'department_id': 'dept_id'})
            dept_dfs.append(emp_dept)
            
        if timesheet_df is not None and not timesheet_df.empty:
            if 'department_id' in timesheet_df.columns:
                ts_dept = timesheet_df[['department_id']].rename(columns={'department_id': 'dept_id'})
                ts_dept['organization_id'] = None
                dept_dfs.append(ts_dept)
            if 'home_department_id' in timesheet_df.columns:
                ts_h_dept = timesheet_df[['home_department_id']].rename(columns={'home_department_id': 'dept_id'})
                ts_h_dept['organization_id'] = None
                dept_dfs.append(ts_h_dept)
                
        if dept_dfs:
            dept_df = pd.concat(dept_dfs, ignore_index=True)
            dept_df['dept_id'] = dept_df['dept_id'].astype(str).str.strip()
            dept_df = dept_df.dropna(subset=['dept_id']).rename(columns={'dept_id': 'department_id'})
            
            if 'department_name' not in dept_df.columns:
                dept_df['department_name'] = 'Dept_' + dept_df['department_id'].astype(str)
                
            dept_df = dept_df.sort_values(by='organization_id', na_position='last')
            dept_df = dept_df.drop_duplicates(subset=['department_id'])
            self._load_dataframe_to_db(dept_df, 'department')

    def _load_manager(self, employee_df: pd.DataFrame):
        """Extracts and loads manager data."""
        if 'manager_employee_id' not in employee_df.columns:
            return
            
        manager_df = employee_df[['manager_employee_id', 'department_id', 'organization_id']].rename(
            columns={'manager_employee_id': 'manager_id'}
        ).dropna(subset=['manager_id'])
        
        if 'manager_employee_name' in employee_df.columns:
            manager_names = employee_df[['manager_employee_id', 'manager_employee_name']].rename(
                columns={'manager_employee_id': 'manager_id', 'manager_employee_name': 'manager_name'}
            ).drop_duplicates(subset=['manager_id'])
            manager_df = manager_df.merge(manager_names, on='manager_id', how='left')
            
        manager_df = manager_df.drop_duplicates(subset=['manager_id'])
        self._load_dataframe_to_db(manager_df, 'manager')

    def _load_employee_job(self, employee_df: pd.DataFrame):
        """Extracts and loads employee_job data."""
        if 'job_code' not in employee_df.columns:
            return
            
        job_df = employee_df[['job_code']].drop_duplicates().dropna(subset=['job_code'])
        if 'job_title' not in job_df.columns:
            job_df['job_title'] = 'Job_' + job_df['job_code'].astype(str)
        if 'clinical_level' not in job_df.columns:
            job_df['clinical_level'] = None
            
        self._load_dataframe_to_db(job_df, 'employee_job')

    def _load_employee(self, employee_df: pd.DataFrame):
        """Extracts, cleans, and loads employee data."""
        emp_cols = [
            'department_id', 'first_name', 'middle_name', 'last_name', 'preferred_name',
            'job_code', 'job_start_date', 'organization_id', 'dob',
            'hire_date', 'recent_hire_date', 'anniversary_date', 'termination_date', 'years_of_experience',
            'work_email', 'address', 'city', 'state', 'zip_code', 'country', 'fte_status',
            'is_per_diem', 'cell_phone', 'work_phone', 'scheduled_weekly_hours', 'active_status', 'termination_reason'
        ]
        emp_base = employee_df.rename(columns={'client_employee_id': 'employee_id', 'manager_employee_id': 'manager_id'})
        existing_emp_cols = ['employee_id', 'manager_id'] + [c for c in emp_cols if c in emp_base.columns]
        emp_final_df = emp_base[existing_emp_cols].drop_duplicates(subset=['employee_id']).dropna(subset=['employee_id'])
        self._load_dataframe_to_db(emp_final_df, 'employee')

    def _load_timesheet(self, timesheet_df: pd.DataFrame):
        """Extracts and loads timesheet data, ensuring referential integrity."""
        ts_cols = [
            'department_id', 'home_department_id', 'client_employee_id',
            'pay_code', 'punch_in_comment', 'punch_out_comment', 'hours_worked',
            'punch_apply_date', 'punch_in_datetime', 'punch_out_datetime'
        ]
        ts_base = timesheet_df.rename(columns={'client_employee_id': 'employee_id'})
        existing_ts_cols = [c for c in ts_cols if c in ts_base.columns]
        if 'employee_id' in ts_base.columns and 'employee_id' not in existing_ts_cols:
            existing_ts_cols.append('employee_id')
        ts_final_df = ts_base[existing_ts_cols].drop_duplicates()
        
        # Check employee exists
        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT employee_id FROM employee"))
            valid_emp_ids = {row[0] for row in res}
        ts_final_df = ts_final_df[ts_final_df['employee_id'].isin(valid_emp_ids)]
        
        # Check departments exist
        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT department_id FROM department"))
            valid_dept_ids = {row[0] for row in res}
        
        if 'department_id' in ts_final_df.columns:
            ts_final_df.loc[~ts_final_df['department_id'].isin(valid_dept_ids), 'department_id'] = None
        if 'home_department_id' in ts_final_df.columns:
            ts_final_df.loc[~ts_final_df['home_department_id'].isin(valid_dept_ids), 'home_department_id'] = None
            
        self._load_dataframe_to_db(ts_final_df, 'timesheet')

    def _load_schedule(self, timesheet_df: pd.DataFrame):
        """Extracts schedule data and maps it to the generated timesheet_id surrogate keys."""
        if 'scheduled_start_datetime' not in timesheet_df.columns or 'scheduled_end_datetime' not in timesheet_df.columns:
            return
            
        ts_base = timesheet_df.rename(columns={'client_employee_id': 'employee_id'})
        sched_cols = ['employee_id', 'punch_in_datetime', 'scheduled_start_datetime', 'scheduled_end_datetime']
        existing_sched_cols = [c for c in sched_cols if c in ts_base.columns]
        
        if 'employee_id' in existing_sched_cols and 'punch_in_datetime' in existing_sched_cols:
            sched_final_df = ts_base[existing_sched_cols].drop_duplicates()
            sched_final_df = sched_final_df.dropna(subset=['scheduled_start_datetime', 'scheduled_end_datetime'], how='all')
            
            if not sched_final_df.empty:
                # Map timesheet_id
                query = "SELECT timesheet_id, employee_id, punch_in_datetime FROM timesheet"
                db_timesheets = pd.read_sql(query, self.engine)
                
                # Normalize timezones for merging
                db_timesheets['punch_in_datetime'] = pd.to_datetime(db_timesheets['punch_in_datetime'], utc=True).dt.tz_localize(None)
                sched_final_df['punch_in_datetime'] = pd.to_datetime(sched_final_df['punch_in_datetime'], utc=True).dt.tz_localize(None)
                
                sched_mapped_df = sched_final_df.merge(db_timesheets, on=['employee_id', 'punch_in_datetime'], how='inner')
                sched_to_insert = sched_mapped_df[['timesheet_id', 'scheduled_start_datetime', 'scheduled_end_datetime']]
                
                self._load_dataframe_to_db(sched_to_insert, 'schedule')

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




