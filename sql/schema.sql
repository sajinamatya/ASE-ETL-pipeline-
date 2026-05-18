-- =============================================================
-- ETL Pipeline DB — Full Schema
-- =============================================================

-- -------------------------------------------------------------
-- Users table (API authentication)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id               SERIAL PRIMARY KEY,
    username         VARCHAR(100) UNIQUE NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    hashed_password  VARCHAR(255)        NOT NULL,
    role             VARCHAR(50)         NOT NULL DEFAULT 'viewer',
    is_active        BOOLEAN             NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------
-- Organization
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organization (
    organization_id   VARCHAR(100) PRIMARY KEY,
    organization_name VARCHAR(255)
);

-- -------------------------------------------------------------
-- Department
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS department (
    department_id   VARCHAR(100) PRIMARY KEY,
    organization_id VARCHAR(100) REFERENCES organization(organization_id),
    department_name VARCHAR(255)
);

-- -------------------------------------------------------------
-- Manager
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manager (
    manager_id        VARCHAR(100) PRIMARY KEY,
    department_id     VARCHAR(100) REFERENCES department(department_id),
    organization_id   VARCHAR(100) REFERENCES organization(organization_id),
    manager_name      VARCHAR(255)
);

-- -------------------------------------------------------------
-- Employee_job
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employee_job (
    job_code       VARCHAR(100) PRIMARY KEY,
    job_title      VARCHAR(255),
    clinical_level VARCHAR(100)
);

-- -------------------------------------------------------------
-- Employee
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employee (
    employee_id           VARCHAR(100) PRIMARY KEY,
    department_id         VARCHAR(100) REFERENCES department(department_id),
    first_name            VARCHAR(100),
    middle_name           VARCHAR(100),
    last_name             VARCHAR(100),
    preferred_name        VARCHAR(100),
    job_code              VARCHAR(100) REFERENCES employee_job(job_code),
    job_start_date        DATE,
    organization_id       VARCHAR(100) REFERENCES organization(organization_id),
    manager_id            VARCHAR(100) REFERENCES manager(manager_id),
    dob                   DATE,
    hire_date             DATE,
    recent_hire_date      DATE,
    anniversary_date      DATE,
    termination_date      DATE,
    years_of_experience   NUMERIC,
    work_email            VARCHAR(255),
    address               TEXT,
    city                  VARCHAR(100),
    state                 VARCHAR(100),
    zip_code              VARCHAR(50),
    country               VARCHAR(100),
    fte_status            VARCHAR(50),
    is_per_diem           BOOLEAN,
    cell_phone            VARCHAR(50),
    work_phone            VARCHAR(50),
    scheduled_weekly_hours NUMERIC,
    active_status         VARCHAR(50),
    termination_reason    TEXT
);

-- -------------------------------------------------------------
-- Timesheet
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS timesheet (
    timesheet_id        SERIAL PRIMARY KEY,
    department_id       VARCHAR(100) REFERENCES department(department_id),
    home_department_id  VARCHAR(100) REFERENCES department(department_id),
    pay_code            VARCHAR(100),
    punch_in_comment    TEXT,
    punch_out_comment   TEXT,
    hours_worked        NUMERIC,
    punch_apply_date    DATE,
    punch_in_datetime   TIMESTAMPTZ,
    punch_out_datetime  TIMESTAMPTZ,
    employee_id         VARCHAR(100) REFERENCES employee(employee_id)
);

-- -------------------------------------------------------------
-- Schedule
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schedule (
    schedule_id              SERIAL PRIMARY KEY,
    timesheet_id             INT REFERENCES timesheet(timesheet_id),
    scheduled_start_datetime TIMESTAMPTZ,
    scheduled_end_datetime   TIMESTAMPTZ
);
