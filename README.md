# ASI ETL Pipeline & Data Warehouse

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.8.1-017CEE.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-009688.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)

An end-to-end Data Engineering pipeline designed to process employee timesheet and HR data. It extracts raw CSVs, loads them into an S3-compatible data lake (MinIO), transforms the data using Pandas, and loads it into a fully normalized **PostgreSQL** database. Finally, it builds a **Star Schema** for reporting and serves the data through a secure **FastAPI** backend.

---

## 🏗 System Architecture & Design

### Work Breakdown Structure
An overview of the pipeline's modular stages (Extract, Transform, Load, API, and Visualization):

![Work Breakdown Structure](documentation%20file/work_breakdown_structure.jpg)

### Database Modeling

The database utilizes a **Two-Tiered (Medallion) Architecture**:
1. **OLTP (Normalized):** Raw data is deduplicated and inserted into strict 3rd Normal Form (3NF) relational tables (`department`, `employee`, `timesheet`).
2. **OLAP (Star Schema):** A downstream SQL process builds a reporting-friendly Star Schema (`fact_timesheet`, `dim_employee`, `dim_department`, `dim_date`) specifically optimized for Power BI and Analytics.

#### Original ERD
![Initial ERD](documentation%20file/initial_ERD%20(2).jpg)

#### Final Star Schema ERD
![Final ERD](documentation%20file/final_ERD.jpg)

*(Detailed PDF explanations for normalization can be found in the `documentation file/` folder).*

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure you have installed:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* Python 3.9+ (Optional: For local development outside of Docker)

### 2. Infrastructure Setup
Clone the repository and set up your environment variables:
```bash
cp .env.example .env
```
*(Open `.env` and configure your passwords if necessary).*

Spin up the Docker containers (PostgreSQL, MinIO, FastAPI, and Apache Airflow):
```bash
docker compose up -d
```

### 3. Initialize the Database
Run the SQL schema scripts to create the tables in your PostgreSQL database:
```bash
docker exec -it asietlpipeline-db-1 psql -U postgres -d etl_db -f sql/schema.sql
```
*(Replace `postgres` and `etl_db` with your `.env` values if changed).*

### 4. Create an Admin User
Initialize the default Admin User (`admin` / `Admin@12345`) for the FastAPI backend:
```bash
docker exec asietlpipeline-api-1 python -c "from api.database import SessionLocal, engine; from api import models; from api.auth import hash_password; models.Base.metadata.create_all(bind=engine); db = SessionLocal(); admin = models.User(username='admin', email='admin@example.com', hashed_password=hash_password('Admin@12345'), role='admin'); db.add(admin); db.commit(); print('Admin Created!')"
```

---

## ⚙️ Running the ETL Pipeline

You can run the ETL pipeline using **Apache Airflow**:
1. Visit the Airflow Web UI at: [http://localhost:8080](http://localhost:8080)
2. Login with credentials set in your `.env` (Default: `admin` / `admin`).
3. Locate the `etl_end_to_end_pipeline` DAG.
4. Toggle the switch to **Unpause** the DAG, then click the **Trigger DAG** (Play) button.
5. Airflow will extract the data, push it to MinIO, transform it utilizing Pandas, and load it into PostgreSQL.

*Alternatively, to run the pipeline manually via CLI:*
```bash
python main.py
```

---

## 📊 Analytics & API

### 🌐 Secure FastAPI Backend
The pipeline exposes processed data through a JWT-secured API. 
* Interactive Swagger Docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**
* To access the endpoints, authenticate via Postman using the `/auth/token` endpoint (URL-encoded: `username=admin`, `password=Admin@12345`).

### 📈 Visualizations
* **Python Generated:** Look in the `visualizations/` folder for automatically generated KPI charts (e.g., Attrition Rate, Overtime).
* **Power BI:** Connect Power BI Desktop to `localhost:5432` (Database: `etl_db`) and import your `dim_` and `fact_` tables.

---

## 📁 Repository Structure
```text
├── api/                   # FastAPI application & routers
├── config/                # Pipeline configurations
├── data/                  # Raw and Processed CSV data buffers
├── documentation file/    # Diagrams, PDFs, and Architecture schemas
├── orchestration/         # Airflow DAGs
├── sql/                   # Database schemas and analytical views
├── src/                   # ETL logic (extract, transform, load, validate)
├── visualizations/        # Generated analytical plots
├── docker-compose.yml     # Docker architecture setup
└── main.py                # Local manual testing script
```