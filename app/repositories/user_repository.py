from sqlalchemy.orm import Session
from typing import Optional
from app.models.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        phone_number: Optional[str] = None,
    ) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            phone_number=phone_number,
        )
        self.db.add(user)
        self.db.flush()  # flush to get ID without committing
        return user

    def email_exists(self, email: str) -> bool:
        return self.db.query(User.id).filter(User.email == email).first() is not None
