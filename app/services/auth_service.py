from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.repositories.user_repository import UserRepository
from app.models.models import User
from app.schemas.auth import UserSignupRequest, UserLoginRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def signup(self, request: UserSignupRequest) -> User:
        """Register a new user. Raises 409 if email already exists."""
        if self.user_repo.email_exists(request.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{request.email}' already exists",
            )
        hashed = hash_password(request.password)
        user = self.user_repo.create(
            email=request.email,
            hashed_password=hashed,
            full_name=request.full_name,
            phone_number=request.phone_number,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, request: UserLoginRequest) -> TokenResponse:
        """Authenticate user and return JWT. Raises 401 on bad credentials."""
        user = self.user_repo.get_by_email(request.email)
        if not user or not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support.",
            )
        token = create_access_token(data={"sub": user.id})
        return TokenResponse(
            access_token=token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def get_current_user(self, user_id: str) -> User:
        """Fetch a user by ID or raise 404."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
