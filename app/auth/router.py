from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.auth.schema import CreateUser
from app.auth.models import User, RefreshToken
from app.auth.database import get_db
from app.auth.security import hash_password, verify_password
from app.auth.tokens import create_access_token, create_refresh_token, refresh_token_expiry
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: CreateUser, db: Session = Depends(get_db)):

    # check whether the user already exists
    exisiting_user = db.query(User).filter(
        User.email_id == user.email
    ).first()

    if exisiting_user:
        raise HTTPException(
            status_code=400,
            detail="User already exisits"
        )
    
    hashed_password = hash_password(user.password)

    new_user = User(
        email_id = user.email,
        user_name = user.name,
        password_hash = hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id" : new_user.id,
        "email" : new_user.email_id,
        "name": new_user.user_name,
        "created_at": new_user.created_at
    }


@router.post("/login")
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    # OAuthPasswordRequestForm will accept username and password. naming standards of OAuth2 only
    # here username is email

    username = user.username
    password = user.password

    existing_user = db.query(User).filter(
        User.email_id == username
    ).first()

    if not existing_user or not verify_password(password, existing_user.password_hash):
        raise HTTPException(
            status_code=404,
            detail="Invalid Email or Password"
        )
    
    access_token = create_access_token(existing_user.id)

    refresh_token = RefreshToken(
        user_id = existing_user.id,
        token = create_refresh_token(),
        expires_at = refresh_token_expiry()
    )

    db.add(refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token.token,
        "token_type": "bearer"
    }


@router.post("/refresh")
def refresh_tokens(refresh_token: str, db: Session = Depends(get_db)):
    
    token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if not token: 
        raise HTTPException(status_code=401, detail="Invalid Refresh token")
    
    if token.revoked:
        refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token
        ).first()
        db.delete(refresh_token)
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Token Reuse Detected. Please Login Again"
        )

    if token.expires_at < datetime.now(timezone.utc):
        db.delete(token)
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Token Expired. Please Login Again"
        )
    
    token.revoked = True

    new_refresh_token = RefreshToken(
        user_id = token.user_id,
        token = create_refresh_token(),
        expires_at = refresh_token_expiry()
    )

    db.add(new_refresh_token)
    db.commit()

    access_token = create_access_token(token.user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if token:
        db.delete(token)
        db.commit()

    return {
        "message": "Logged Out Successfully"
    }