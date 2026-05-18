"""
Auth router — user registration and JWT token issuance.

Endpoints:
  POST /auth/register  →  create account (admin only to prevent open sign-up)
  POST /auth/token     →  OAuth2 password flow, returns Bearer token
  GET  /auth/me        →  current authenticated user info
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api import models, schemas
from api.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_user_by_username,
    hash_password,
    require_admin,
)
from api.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new API user (admin only)",
)
def register_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),  # only admins can create users
):
    logger.info(f"Attempting to register new user: {payload.username}")
    if get_user_by_username(db, payload.username):
        logger.warning(f"Registration failed: Username '{payload.username}' taken.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' is already taken.",
        )
    if db.query(models.User).filter(models.User.email == payload.email).first():
        logger.warning(f"Registration failed: Email '{payload.email}' already registered.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{payload.email}' is already registered.",
        )

    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"User {user.username} successfully registered.")
    return user


@router.post(
    "/token",
    response_model=schemas.Token,
    summary="Obtain a JWT access token (OAuth2 password flow)",
)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    logger.info(f"Login attempt for user: {form_data.username}")
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username, "role": user.role})
    logger.info(f"User {user.username} successfully logged in.")
    return schemas.Token(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=schemas.UserResponse,
    summary="Return the currently authenticated user",
)
def read_current_user(current_user: Annotated[models.User, Depends(get_current_user)]):
    return current_user
