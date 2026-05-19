import os
import sys
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from airflow import DAG
from airflow.operators.python import PythonOperator

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.extract import ExtractEmployee, ExtractTimesheet
from src.transform import transform_employee, transform_timesheet
from src.load import DataLoader

# Paths and URLs
DATASET_PATH = os.environ.get("DATASET_PATH", r"C:\Users\LENOVO\Downloads\ASE-ETL-dataset_1_1 (1)")
PROCESSED_DIR = os.environ.get("PROCESSED_DIR", os.path.join(os.path.dirname(__file__), '..', 'data', 'processed'))

# DOCKER_DATABASE_URL is used inside the Airflow Docker container
DB_URL = os.environ.get("DOCKER_DATABASE_URL", os.environ.get("DATABASE_URL"))

# MinIO configs (Optional)
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")

def task_extract_employee():
    logger.info(f"Starting extraction of employee data from {DATASET_PATH}")
    try:
        extractor = ExtractEmployee(DATASET_PATH, PROCESSED_DIR)
        return extractor.run()
    except Exception as e:
        logger.error(f"Error during employee extraction: {e}")
        raise

def task_extract_timesheets():
    logger.info(f"Starting extraction of timesheet data from {DATASET_PATH}")
    try:
        extractor = ExtractTimesheet(DATASET_PATH, PROCESSED_DIR)
        return extractor.run()
    except Exception as e:
        logger.error(f"Error during timesheet extraction: {e}")
        raise

def task_transform_employee():
    logger.info("Starting transformation of employee data")
    try:
        input_path = os.path.join(PROCESSED_DIR, 'extracted_employee.parquet')
        output_path = os.path.join(PROCESSED_DIR, 'transformed_employee.parquet')
        df = pd.read_parquet(input_path)
        df_transformed = transform_employee(df)
        df_transformed.to_parquet(output_path, index=False)
        logger.info(f"Successfully transformed employee data saved to {output_path}")
    except Exception as e:
        logger.error(f"Error during employee transformation: {e}")
        raise

def task_transform_timesheets():
    logger.info("Starting transformation of timesheet data")
    try:
        input_path = os.path.join(PROCESSED_DIR, 'extracted_timesheets.parquet')
        output_path = os.path.join(PROCESSED_DIR, 'transformed_timesheets.parquet')
        df = pd.read_parquet(input_path)
        df_transformed = transform_timesheet(df)
        df_transformed.to_parquet(output_path, index=False)
        logger.info(f"Successfully transformed timesheet data saved to {output_path}")
    except Exception as e:
        logger.error(f"Error during timesheet transformation: {e}")
        raise

def task_load_normalized_data():
    logger.info("Starting normalized insert into database respecting ERD constraints")
    try:
        # DataLoader supports both local DataFrame operations and MinIO operations
        loader = DataLoader(
            db_url=DB_URL,
            minio_endpoint=MINIO_ENDPOINT,
            minio_access_key=MINIO_ACCESS_KEY,
            minio_secret_key=MINIO_SECRET_KEY
        )
        emp_path = os.path.join(PROCESSED_DIR, 'transformed_employee.parquet')
        ts_path = os.path.join(PROCESSED_DIR, 'transformed_timesheets.parquet')
        
        employee_df = pd.read_parquet(emp_path) if os.path.exists(emp_path) else pd.DataFrame()
        timesheet_df = pd.read_parquet(ts_path) if os.path.exists(ts_path) else pd.DataFrame()

        loader.load_normalized_data(employee_df, timesheet_df)
        logger.info("Normalized database insert completed")
    except Exception as e:
        logger.error(f"Error during loading data to database: {e}")
        raise

def task_post_processing():
    """
    Run quality control checks, generate dimensional (Star Schema) tables, and run business reports/visualizations.
    """
    logger.info("Starting post-processing routines (Dimensional modeling & Analysis)...")
    try:
        loader = DataLoader(
            db_url=DB_URL,
            minio_endpoint=MINIO_ENDPOINT,
            minio_access_key=MINIO_ACCESS_KEY,
            minio_secret_key=MINIO_SECRET_KEY
        )
        
        # 1. Generate Star Schema from Normalized data (Medallion: Silver -> Gold)
        logger.info("Executing Medallion Gold Layer: Building dimensional star schema...")
        sql_schema_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'build_star_schema.sql')
        loader.execute_sql_script(sql_schema_path)
        
        # 1b. Create Analytics Views for Power BI
        logger.info("Deploying Analytics KPI Views for Power BI...")
        sql_views_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'analytics_views.sql')
        loader.execute_sql_script(sql_views_path)
        
        # 2. Run Data Quality Validation Scripts
        from src.validate import DataValidator
        logger.info("Executing Post-load Data Quality Checks...")
        validator = DataValidator(db_url=DB_URL)
        validator.run_all_checks()
        
        # 3. Generate Visualizations & Automated Reports (Matplotlib -> PNG)
        from src.visualize import generate_visualizations
        out_dir = os.path.join(os.path.dirname(__file__), '..', 'visualizations')
        os.makedirs(out_dir, exist_ok=True)
        generate_visualizations(DB_URL, out_dir)
        logger.info("Automated visualization reporting generated successfully.")
    except Exception as e:
        logger.error(f"Error during post-processing: {e}")
        raise

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='etl_end_to_end_pipeline',
    default_args=default_args,
    description='End-to-End ETL pipeline',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['etl', 'full-pipeline'],
) as dag:

    # Extract
    extract_emp = PythonOperator(task_id='extract_employee', python_callable=task_extract_employee)
    extract_ts = PythonOperator(task_id='extract_timesheets', python_callable=task_extract_timesheets)
    
    # Transform
    transform_emp = PythonOperator(task_id='transform_employee', python_callable=task_transform_employee)
    transform_ts = PythonOperator(task_id='transform_timesheets', python_callable=task_transform_timesheets)
    
    # Load (Merged normalized inserts)
    load_db = PythonOperator(task_id='load_normalized_data', python_callable=task_load_normalized_data)
    
    # Post-Processing
    post_process = PythonOperator(task_id='post_processing', python_callable=task_post_processing)
    
    # Dependencies
    extract_emp >> transform_emp
    extract_ts >> transform_ts
    
    # Both transformations must complete before sending to load_normalized_data
    [transform_emp, transform_ts] >> load_db
    
    # Ensure database is loaded before post-processing
    load_db >> post_process

