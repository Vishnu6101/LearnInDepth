from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.sql import func
from app.auth.database import Base
from app.auth.utils.common.ids import generate_id

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: generate_id("usr"))
    email_id = Column(String, unique=True, nullable=False, index=True)
    user_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    __table_args__ = (
        UniqueConstraint("session_id", "token"),
    )

    id = Column(String, primary_key=True, default=lambda: generate_id("rft"))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"))
    token = Column(String, unique=True, nullable=False, index=True)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


class Sessions(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: generate_id("ses"))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    fingerprint_hash = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())