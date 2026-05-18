-- =============================================================
-- Analytics KPIs - Views for Power BI connection
-- =============================================================

-- 1. Active Headcount Over Time (Monthly snapshot)
CREATE OR REPLACE VIEW v_active_headcount AS
WITH months AS (
    SELECT generate_series(
        DATE_TRUNC('month', MIN(hire_date)), 
        DATE_TRUNC('month', CURRENT_DATE), 
        '1 month'::interval
    ) AS snapshot_month
    FROM employee
)
SELECT 
    m.snapshot_month,
    COUNT(e.employee_id) AS active_headcount
FROM months m
LEFT JOIN employee e 
    ON DATE_TRUNC('month', e.hire_date) <= m.snapshot_month
    AND (e.termination_date IS NULL OR DATE_TRUNC('month', e.termination_date) > m.snapshot_month)
GROUP BY m.snapshot_month;


-- 2. Turnover Trend (Monthly)
CREATE OR REPLACE VIEW v_turnover_trend AS
SELECT 
    DATE_TRUNC('month', termination_date) AS termination_month,
    COUNT(employee_id) AS turnover_count
FROM employee
WHERE termination_date IS NOT NULL
GROUP BY DATE_TRUNC('month', termination_date);


-- 3. Average Tenure by Department
CREATE OR REPLACE VIEW v_avg_tenure_by_department AS
SELECT 
    d.department_name,
    AVG(
        EXTRACT(EPOCH FROM (COALESCE(e.termination_date, CURRENT_DATE) - e.hire_date)) / 31557600
    ) AS avg_tenure_years
FROM employee e
JOIN department d ON e.department_id = d.department_id
GROUP BY d.department_name;


-- 4. Average Working Hours per Employee
CREATE OR REPLACE VIEW v_avg_working_hours AS
SELECT 
    e.employee_id,
    e.first_name,
    e.last_name,
    AVG(f.hours_worked) AS avg_hours_per_shift
FROM fact_timesheet f
JOIN dim_employee e ON f.employee_sk = e.employee_sk
GROUP BY e.employee_id, e.first_name, e.last_name;


-- 5. Late Arrival Frequency (Grace time +5 min)
CREATE OR REPLACE VIEW v_late_arrivals AS
SELECT 
    t.employee_id,
    COUNT(*) AS late_arrival_count
FROM timesheet t
JOIN schedule s ON t.timesheet_id = s.timesheet_id
WHERE t.punch_in_datetime > (s.scheduled_start_datetime + INTERVAL '5 minutes')
GROUP BY t.employee_id;


-- 6. Early Departure Count (Grace time -5 min)
CREATE OR REPLACE VIEW v_early_departures AS
SELECT 
    t.employee_id,
    COUNT(*) AS early_departure_count
FROM timesheet t
JOIN schedule s ON t.timesheet_id = s.timesheet_id
WHERE t.punch_out_datetime < (s.scheduled_end_datetime - INTERVAL '5 minutes')
GROUP BY t.employee_id;


-- 7. Total Overtime Count (Exceeding standard 8-hour shift, with 5 min grace)
CREATE OR REPLACE VIEW v_total_overtime AS
SELECT 
    employee_id,
    SUM(CASE WHEN hours_worked > (8.0 + (5.0/60.0)) THEN 1 ELSE 0 END) AS overtime_shifts_count,
    SUM(CASE WHEN hours_worked > (8.0 + (5.0/60.0)) THEN (hours_worked - 8.0) ELSE 0 END) AS total_overtime_hours
FROM timesheet
GROUP BY employee_id;


-- 8. Rolling Average Working Hours (7-day moving average)
CREATE OR REPLACE VIEW v_rolling_avg_hours AS
SELECT 
    date_sk AS work_date,
    employee_sk,
    hours_worked,
    AVG(hours_worked) OVER (
        PARTITION BY employee_sk 
        ORDER BY date_sk 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7day_avg_hours
FROM fact_timesheet;


-- 9. Early Attrition Rate (Left within 6 months of joining)
CREATE OR REPLACE VIEW v_early_attrition AS
WITH attrition_flags AS (
    SELECT 
        employee_id,
        CASE 
            WHEN termination_date IS NOT NULL AND (termination_date - hire_date) <= 180 THEN 1 
            ELSE 0 
        END AS is_early_attrition
    FROM employee
)
SELECT 
    SUM(is_early_attrition) * 100.0 / COUNT(*) AS early_attrition_rate_pct
FROM attrition_flags;
