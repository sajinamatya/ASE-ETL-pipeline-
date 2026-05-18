-- =============================================================
-- Dimensional Model (Star Schema) - Gold Layer
-- =============================================================

-- Drop existing tables to rebuild (for batch ETL idempotent runs)
DROP TABLE IF EXISTS fact_timesheet CASCADE;
DROP TABLE IF EXISTS dim_employee CASCADE;
DROP TABLE IF EXISTS dim_department CASCADE;
DROP TABLE IF EXISTS dim_job CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;

-- 1. dim_department
CREATE TABLE dim_department AS
SELECT 
    d.department_id AS department_sk,
    d.department_name,
    o.organization_name
FROM department d
LEFT JOIN organization o ON d.organization_id = o.organization_id;

-- 2. dim_job
CREATE TABLE dim_job AS
SELECT 
    job_code AS job_sk,
    job_title,
    clinical_level
FROM employee_job;

-- 3. dim_employee
CREATE TABLE dim_employee AS
SELECT 
    e.employee_id AS employee_sk,
    e.first_name,
    e.last_name,
    e.hire_date,
    e.termination_date,
    e.is_per_diem,
    e.active_status,
    m.manager_name
FROM employee e
LEFT JOIN manager m ON e.manager_id = m.manager_id;

-- 4. dim_date (Generated dynamically from the timesheet facts)
CREATE TABLE dim_date AS
SELECT DISTINCT 
    punch_apply_date AS date_sk,
    EXTRACT(YEAR FROM punch_apply_date) AS year,
    EXTRACT(MONTH FROM punch_apply_date) AS month,
    EXTRACT(DAY FROM punch_apply_date) AS day,
    EXTRACT(ISODOW FROM punch_apply_date) AS day_of_week
FROM timesheet
WHERE punch_apply_date IS NOT NULL;

-- 5. fact_timesheet
CREATE TABLE fact_timesheet AS
SELECT 
    t.timesheet_id AS timesheet_sk,
    t.punch_apply_date AS date_sk,
    t.employee_id AS employee_sk,
    t.department_id AS department_sk,
    e.job_code AS job_sk,
    t.hours_worked,
    CASE WHEN t.hours_worked > 8 THEN (t.hours_worked - 8) ELSE 0 END AS overtime_hours,
    CASE WHEN t.hours_worked > 8 THEN TRUE ELSE FALSE END AS is_overtime,
    t.pay_code
FROM timesheet t
LEFT JOIN employee e ON t.employee_id = e.employee_id;

-- Create basic indexes for the warehouse to improve query performance
CREATE INDEX idx_fact_ts_date ON fact_timesheet(date_sk);
CREATE INDEX idx_fact_ts_emp ON fact_timesheet(employee_sk);
CREATE INDEX idx_fact_ts_dept ON fact_timesheet(department_sk);

