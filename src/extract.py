import os
import logging
import pandas as pd
from pathlib import Path
from typing import Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExtractEmployee:
    """
    Class to extract employee data from raw CSV files and save as parquet.
    """
    def __init__(self, dataset_dir: Union[str, Path], processed_dir: Union[str, Path]):
        self.dataset_dir = Path(dataset_dir)
        self.processed_dir = Path(processed_dir)

    def require(self):
        return []

    def output(self):
        processed_path = self.processed_dir
        os.makedirs(processed_path, exist_ok=True)
        return processed_path / 'extracted_employee.parquet'

    def run(self):
        try:
            employee_files = list(self.dataset_dir.rglob("employee_*.csv"))
            if not employee_files:
                logger.error(f"No employee CSV found in {self.dataset_dir}")
                raise FileNotFoundError(f"No employee CSV found in {self.dataset_dir}")
                
            logger.info(f"Extracting employee data from {employee_files[0]}")
            df = pd.read_csv(employee_files[0], sep="|", low_memory=False)
            
            # Fix mixed-type schema errors for PyArrow
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str)
            
            output_path = self.output()
            df.to_parquet(output_path, index=False)
            logger.info(f"Employee data successfully extracted and saved to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed during employee extraction: {e}", exc_info=True)
            raise


class ExtractTimesheet:
    """
    Class to extract and merge timesheet CSV files, and save as parquet.
    """
    def __init__(self, dataset_dir: Union[str, Path], processed_dir: Union[str, Path]):
        self.dataset_dir = Path(dataset_dir)
        self.processed_dir = Path(processed_dir)

    def require(self):
        return [ExtractEmployee(self.dataset_dir, self.processed_dir)]

    def output(self):
        processed_path = self.processed_dir
        os.makedirs(processed_path, exist_ok=True)
        return processed_path / 'extracted_timesheets.parquet'

    def run(self):
        try:
            timesheet_files = list(self.dataset_dir.rglob("timesheet_*.csv"))
            if not timesheet_files:
                logger.error(f"No timesheet CSVs found in {self.dataset_dir}")
                raise FileNotFoundError(f"No timesheet CSVs found in {self.dataset_dir}")
                
            logger.info(f"Extracting timesheet data from {len(timesheet_files)} files")
            df = pd.concat(
                (pd.read_csv(file, sep="|", low_memory=False) for file in timesheet_files),
                ignore_index=True
            )
            
            # Fix mixed-type schema errors for PyArrow
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str)
            
            output_path = self.output()
            df.to_parquet(output_path, index=False)
            logger.info(f"Timesheet data successfully extracted and saved to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed during timesheets extraction: {e}", exc_info=True)
            raise
