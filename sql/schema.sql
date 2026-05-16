-- =============================================================
-- ETL Pipeline DB — Employees & Timesheets schema
-- Run this manually only if you need to pre-create tables
-- before launching the API (the API auto-creates them on boot).
-- =============================================================

-- Users table (API authentication)
CREATE TABLE IF NOT EXISTS users (
    id               SERIAL PRIMARY KEY,
    username         VARCHAR(100) UNIQUE NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    hashed_password  VARCHAR(255)        NOT NULL,
    role             VARCHAR(50)         NOT NULL DEFAULT 'viewer',
    is_active        BOOLEAN             NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

-- Employees table
CREATE TABLE IF NOT EXISTS employees (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(150) NOT NULL,
    email        VARCHAR(255) UNIQUE NOT NULL,
    department   VARCHAR(100) NOT NULL,
    role         VARCHAR(100) NOT NULL,
    date_joined  DATE         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on every row change
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_employees_updated_at ON employees;
CREATE TRIGGER set_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Timesheets table
CREATE TABLE IF NOT EXISTS timesheets (
    id            SERIAL PRIMARY KEY,
    employee_id   INT          NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    work_date     DATE         NOT NULL,
    hours_worked  FLOAT        NOT NULL,
    project       VARCHAR(200),
    notes         VARCHAR(500),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_timesheets_employee_id ON timesheets(employee_id);
CREATE INDEX IF NOT EXISTS idx_timesheets_work_date   ON timesheets(work_date);
CREATE INDEX IF NOT EXISTS idx_employees_department    ON employees(department);
