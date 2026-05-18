import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def transform_employee(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans employee data and creates derived business metrics.
    """
    logger.info("Starting employee transformation rules...")
    try:
        # 1. Remove duplicates
        df = df.drop_duplicates()
        
        # 2. Trim extra spaces for string columns
        str_cols = df.select_dtypes(include=['object', 'string']).columns
        for col in str_cols:
            df[col] = df[col].astype(str).str.strip()
            
        # 3. Handle missing values
        if 'department_id' in df.columns:
            df['department_id'] = df['department_id'].fillna('Unknown')
        if 'years_of_experience' in df.columns:
            df['years_of_experience'] = pd.to_numeric(df['years_of_experience'], errors='coerce').fillna(0)
        
        # 4. Correct data types (Dates)
        date_cols = ['job_start_date', 'dob', 'hire_date', 'recent_hire_date', 'anniversary_date', 'termination_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
        # 5. Create derived columns (Business Metrics)
        # Tenure in years
        if 'hire_date' in df.columns:
            df['tenure_years'] = (pd.Timestamp.now() - df['hire_date']).dt.days / 365.25
            
        logger.info("Employee transformation completed successfully.")
        return df
    except Exception as e:
        logger.error(f"Error transforming employee data: {e}", exc_info=True)
        raise


def transform_timesheet(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans timesheet data and creates derived business metrics.
    """
    logger.info("Starting timesheet transformation rules...")
    try:
        # 1. Remove duplicates
        df = df.drop_duplicates()
        
        # 2. Trim extra spaces for string columns
        str_cols = df.select_dtypes(include=['object', 'string']).columns
        for col in str_cols:
            df[col] = df[col].astype(str).str.strip()
            
        # 3. Handle missing values
        if 'hours_worked' in df.columns:
            df['hours_worked'] = pd.to_numeric(df['hours_worked'], errors='coerce').fillna(0)
        if 'punch_in_comment' in df.columns:
            df['punch_in_comment'] = df['punch_in_comment'].replace('nan', '').fillna('')
        if 'punch_out_comment' in df.columns:
            df['punch_out_comment'] = df['punch_out_comment'].replace('nan', '').fillna('')
        
        # 4. Correct data types (Dates/Times)
        date_cols = ['punch_apply_date', 'punch_in_datetime', 'punch_out_datetime']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
        # 5. Create derived columns (Business Metrics)
        if 'hours_worked' in df.columns:
            # Flag if the shift had overtime (Assuming standard 8-hour shift)
            df['is_overtime'] = df['hours_worked'] > 8
            # Calculate exactly how many hours of overtime
            df['overtime_hours'] = df['hours_worked'].apply(lambda x: x - 8 if x > 8 else 0)
        
        logger.info("Timesheets transformation completed successfully.")
        return df
    except Exception as e:
        logger.error(f"Error transforming timesheet data: {e}", exc_info=True)
        raise


