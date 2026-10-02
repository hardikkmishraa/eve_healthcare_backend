from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user_id
from app.core.cache import limiter
from app.core.config import settings
from app.services.auth_service import AuthService
from app.schemas.auth import UserSignupRequest, UserLoginRequest, UserResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def signup(request: Request, body: UserSignupRequest, db: Session = Depends(get_db)):
    """
    Register a new patient account.

    - **email**: Must be unique across the system
    - **password**: Minimum 8 chars, must include 1 uppercase letter and 1 digit
    - **full_name**: Required
    - **phone_number**: Optional
    """
    service = AuthService(db)
    return service.signup(body)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT access token",
)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, body: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a Bearer JWT token.

    Use the returned `access_token` in the `Authorization: Bearer <token>` header
    for all protected endpoints.

    **Rate limit:** 5 attempts/minute per IP — brute-force protection.
    """
    service = AuthService(db)
    return service.login(body)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_me(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Returns the profile of the currently authenticated user."""
    service = AuthService(db)
    return service.get_current_user(user_id)
