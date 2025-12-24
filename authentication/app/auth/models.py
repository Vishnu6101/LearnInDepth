from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.auth.database import Base
from app.auth.utils.ids import generate_id

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: generate_id("usr"))
    email_id = Column(String, unique=True, nullable=False, index=True)
    user_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: generate_id("rft"))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    token = Column(String, unique=True, nullable=False, index=True)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

