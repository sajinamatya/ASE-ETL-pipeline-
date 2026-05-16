"""
FastAPI application entry point.

Start with:
    uvicorn api.main:app --reload

Interactive docs available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import engine
from api import models
from api.routers import auth, employees, timesheets


# ─────────────────────────── Lifespan ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup (idempotent — safe to run repeatedly)."""
    models.Base.metadata.create_all(bind=engine)
    yield
    # Nothing to tear down — connection pool closes automatically


# ─────────────────────────── App ─────────────────────────────────────

app = FastAPI(
    title="ASI ETL Pipeline — Employee & Timesheet API",
    description="""
## Overview
A RESTful API for managing **employee** records and accessing **timesheet** data
within the ASI ETL Pipeline.

## Authentication
All endpoints require a valid JWT Bearer token.  
Obtain one via **POST /auth/token** using your credentials.

## Roles
| Role    | Employees      | Timesheets |
|---------|----------------|------------|
| admin   | Full CRUD      | Read-only  |
| viewer  | Read-only      | Read-only  |

## Quick Start
1. Seed the first admin: `python -m api.seed`
2. `POST /auth/token` with `username` & `password`
3. Use the returned token as `Authorization: Bearer <token>`
""",
    version="1.0.0",
    contact={"name": "ASI ETL Team"},
    lifespan=lifespan,
)

# ─────────────────────────── Middleware ──────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────── Routers ─────────────────────────────────

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(timesheets.router)


# ─────────────────────────── Health ──────────────────────────────────

@app.get("/health", tags=["Health"], summary="Liveness probe")
def health_check():
    return {"status": "ok", "service": "employee-timesheet-api"}
