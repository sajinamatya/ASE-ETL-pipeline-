-- =============================================================
-- Dimensional Model (Star Schema) - Gold Layer
-- =============================================================

-- Drop existing tables to rebuild (for batch ETL idempotent runs)
DROP TABLE IF EXISTS fact_timesheet CASCADE;
DROP TABLE IF EXISTS dim_employee CASCADE;
DROP TABLE IF EXISTS dim_department CASCADE;
DROP TABLE IF EXISTS dim_job CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS dim_manager CASCADE;
DROP TABLE IF EXISTS dim_schedule CASCADE;

-- 1. dim_department
CREATE TABLE dim_department AS
SELECT 
    d.department_id AS dim_department_key,
    d.department_id,
    d.department_name,
    o.organization_id,
    o.organization_name
FROM department d
LEFT JOIN organization o ON d.organization_id = o.organization_id;

-- 2. dim_job
CREATE TABLE dim_job AS
SELECT 
    job_code AS dim_job_key,
    job_code,
    job_title,
    clinical_level
FROM employee_job;

-- 3. dim_manager
CREATE TABLE dim_manager AS
SELECT 
    m.manager_id AS dim_manager_key,
    m.manager_id,
    m.manager_name AS manager_employee_name,
    m.department_id,
    d.department_name,
    m.organization_id,
    o.organization_name
FROM manager m
LEFT JOIN department d ON m.department_id = d.department_id
LEFT JOIN organization o ON m.organization_id = o.organization_id;

-- 4. dim_schedule
CREATE TABLE dim_schedule AS
SELECT 
    s.schedule_id AS dim_schedule_key,
    s.schedule_id AS scheduled_id,
    s.scheduled_start_datetime,
    s.scheduled_end_datetime,
    EXTRACT(EPOCH FROM (s.scheduled_end_datetime - s.scheduled_start_datetime))/3600 AS scheduled_hours
FROM schedule s;

-- 5. dim_employee
CREATE TABLE dim_employee AS
SELECT 
    e.employee_id AS dim_employee_key,
    e.employee_id AS client_employee_id,
    e.first_name,
    e.middle_name,
    e.last_name,
    e.preferred_name,
    e.dob,
    e.hire_date,
    e.recent_hire_date,
    e.anniversary_date,
    e.termination_date AS term_date,
    e.termination_reason,
    e.job_start_date,
    e.years_of_experience,
    e.fte_status,
    e.is_per_diem,
    e.active_status,
    e.scheduled_weekly_hours AS scheduled_weekly_hour,
    e.work_email,
    e.cell_phone,
    e.work_phone,
    e.city,
    e.state,
    e.zip_code AS zip,
    e.country
FROM employee e;

-- 6. dim_date (Generated dynamically from the timesheet facts)
CREATE TABLE dim_date AS
SELECT DISTINCT 
    punch_apply_date AS dim_date_key,
    punch_apply_date AS full_date,
    EXTRACT(ISODOW FROM punch_apply_date) AS day_of_week,
    TO_CHAR(punch_apply_date, 'Day') AS day_name,
    EXTRACT(WEEK FROM punch_apply_date) AS week_number,
    EXTRACT(MONTH FROM punch_apply_date) AS month_number,
    TO_CHAR(punch_apply_date, 'Month') AS month_name,
    CASE WHEN EXTRACT(ISODOW FROM punch_apply_date) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend,
    NULL::VARCHAR AS fiscal_period
FROM timesheet
WHERE punch_apply_date IS NOT NULL;

-- 7. fact_timesheet
CREATE TABLE fact_timesheet AS
SELECT 
    t.timesheet_id,
    t.employee_id AS dim_employee_key,
    t.department_id AS dim_department_key,
    t.home_department_id AS dim_home_dept_key,
    e.job_code AS dim_job_key,
    t.punch_apply_date AS dim_date_key,
    s.schedule_id AS dim_schedule_key,
    e.manager_id AS dim_manager_key,
    t.hours_worked,
    t.pay_code,
    t.punch_in_datetime,
    t.punch_out_datetime,
    t.punch_in_comment,
    t.punch_out_comment
FROM timesheet t
LEFT JOIN employee e ON t.employee_id = e.employee_id
LEFT JOIN schedule s ON t.timesheet_id = s.timesheet_id;

-- Create basic indexes for the warehouse to improve query performance
CREATE INDEX idx_fact_ts_date ON fact_timesheet(dim_date_key);
CREATE INDEX idx_fact_ts_emp ON fact_timesheet(dim_employee_key);
CREATE INDEX idx_fact_ts_dept ON fact_timesheet(dim_department_key);
CREATE INDEX idx_fact_ts_job ON fact_timesheet(dim_job_key);
CREATE INDEX idx_fact_ts_mgr ON fact_timesheet(dim_manager_key);

