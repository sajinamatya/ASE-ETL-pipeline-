import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from pathlib import Path

logger = logging.getLogger(__name__)

def generate_visualizations(db_url: str, output_dir: str):
    """
    Connects to the database, queries the analytic datasets (Power BI Views),
    and generates automated report visualization images.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url)
    
    # Set the style
    plt.style.use('ggplot')
    
    logger.info("Generating automated visualization reports...")
    
    # Visualization 1: Active Headcount Over Time
    try:
        df_hc = pd.read_sql("SELECT * FROM v_active_headcount ORDER BY snapshot_month", engine)
        if not df_hc.empty:
            plt.figure(figsize=(10, 6))
            plt.plot(df_hc['snapshot_month'], df_hc['active_headcount'], marker='o', linestyle='-', color='teal')
            plt.title('Active Employee Headcount Over Time')
            plt.xlabel('Date')
            plt.ylabel('Active Employees')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'active_headcount_trend.png'))
            plt.close()
            logger.info("Saved visualization: active_headcount_trend.png")
    except Exception as e:
        logger.error(f"Failed to generate headcount chart: {e}", exc_info=True)

    # Visualization 2: Average Tenure by Department
    try:
        df_tenure = pd.read_sql("SELECT * FROM v_avg_tenure_by_department ORDER BY avg_tenure_years DESC", engine)
        if not df_tenure.empty:
            plt.figure(figsize=(10, 6))
            plt.bar(df_tenure['department_name'], df_tenure['avg_tenure_years'], color='coral')
            plt.title('Average Employee Tenure by Department')
            plt.xlabel('Department Name')
            plt.ylabel('Average Tenure (Years)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'avg_tenure_by_dept.png'))
            plt.close()
            logger.info("Saved visualization: avg_tenure_by_dept.png")
    except Exception as e:
        logger.error(f"Failed to generate tenure chart: {e}", exc_info=True)

    # Visualization 3: Top Overtime Hours
    try:
        query = """
        SELECT 
            e.first_name || ' ' || e.last_name AS employee_name, 
            v.total_overtime_hours 
        FROM v_total_overtime v
        JOIN employee e ON v.employee_id = e.employee_id
        ORDER BY v.total_overtime_hours DESC 
        LIMIT 10
        """
        df_ot = pd.read_sql(query, engine)
        if not df_ot.empty:
            plt.figure(figsize=(10, 6))
            plt.bar(df_ot['employee_name'], df_ot['total_overtime_hours'], color='purple')
            plt.title('Top 10 Employees by Overtime Hours')
            plt.xlabel('Employee Name')
            plt.ylabel('Total Overtime Hours Exceeding Standard Shifts')
            plt.xticks(rotation=45, ha='right') # Rotate and align right for long names
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'top_overtime_employees.png'))
            plt.close()
            logger.info("Saved visualization: top_overtime_employees.png")
    except Exception as e:
        logger.error(f"Failed to generate overtime chart: {e}", exc_info=True)

    # Visualization 4: Early Attrition Rate
    try:
        df_attr = pd.read_sql("SELECT early_attrition_rate_pct FROM v_early_attrition", engine)
        if not df_attr.empty and not df_attr['early_attrition_rate_pct'].isnull().all():
            rate = float(df_attr['early_attrition_rate_pct'].iloc[0])
            plt.figure(figsize=(8, 4))
            plt.barh(['Early Attrition Rate'], [rate], color='crimson')
            plt.xlim(0, max(100, rate + 10)) # Ensure 100% scale unless it exceeds
            plt.title('Early Attrition Rate (Left within 6 months)')
            plt.xlabel('Percentage (%)')
            # Add data label
            plt.text(rate + 1, 0, f"{rate:.1f}%", va='center', fontweight='bold')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'early_attrition_rate.png'))
            plt.close()
            logger.info("Saved visualization: early_attrition_rate.png")
    except Exception as e:
        logger.error(f"Failed to generate early attrition chart: {e}", exc_info=True)


