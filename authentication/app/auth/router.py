from fastapi import APIRouter, Depends, status, HTTPException, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.auth.schema import CreateUser
from app.auth.models import User, RefreshToken, Sessions
from app.auth.database import get_db
from app.auth.utils.security.password_hash import hash_password, verify_password
from app.auth.utils.security.fingerprint import generate_fingerprint
from app.auth.tokens import create_access_token, create_refresh_token, refresh_token_expiry
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.jwt_dependency import get_current_user_id
from app.auth.clients.redis import get_redis_connection
from redis import Redis

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
        user: CreateUser, 
        db: Session = Depends(get_db)
    ):

    # check whether the user already exists
    exisiting_user = db.query(User).filter(
        User.email_id == user.email
    ).first()

    if exisiting_user:
        raise HTTPException(
            status_code=400,
            detail="User already exisits"
        )
    
    # hashing password
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
def login(
        request: Request, 
        response: Response,
        user: OAuth2PasswordRequestForm = Depends(), 
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_connection)
    ):

    # OAuthPasswordRequestForm will accept username and password. naming standards of OAuth2 only
    # here username is email

    username = user.username
    password = user.password

    # checking if user exisits and passowrd matches
    existing_user = db.query(User).filter(
        User.email_id == username
    ).first()

    if not existing_user or not verify_password(password, existing_user.password_hash):
        raise HTTPException(
            status_code=404,
            detail="Invalid Email or Password"
        )
    
    # Creating a session fingerprint
    user_agent = request.headers.get("user-agent")
    accept_language = request.headers.get("accept-language")

    fingerprint_hash = generate_fingerprint(
        user_agent=user_agent,
        accept_language=accept_language
    )
    
    # creating a new session for user
    session = Sessions(
        user_id = existing_user.id,
        fingerprint_hash = fingerprint_hash,
        user_agent = user_agent, 
        ip_address = request.client.host
    )

    db.add(session)
    db.flush()

    # creating a new refresh token for the session
    refresh_token = RefreshToken(
        session_id = session.id,
        token = create_refresh_token(),
        expires_at = refresh_token_expiry()
    )
    
    db.add(refresh_token)
    db.commit()

    # creating new access token
    access_token = create_access_token(existing_user.id, session.id)
    
    # Storing session info in redis with expiration
    redis_client.set(
        name=f"session:{session.id}",
        value="active",
        ex=60 * 60 * 24 * 30  # 30 days
    )
    
    # setting refresh token in cookies
    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        httponly=True,
        secure=False,     # True
        samesite="lax",   # "strict"
        path="/"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
def refresh_tokens(
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_connection)
    ):

    # Get refresh token from cookies
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing Refresh token")
    
    # check if token is valid
    token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if not token: 
        raise HTTPException(status_code=401, detail="Invalid Refresh token")
    
    # Token reuse - not allowed to refresh
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

    # expired tokens - not allowed to refresh
    if token.expires_at < datetime.now(timezone.utc):
        db.delete(token)
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Token Expired. Please Login Again"
        )
    
    # Token is valid, not resued and not expired
    # checking for active session
    session = db.query(Sessions).filter(
        Sessions.id == token.session_id,
        Sessions.is_active == True
    ).first()

    if not session or not redis_client.exists(f"session:{session.id}"):
        raise HTTPException(status_code=401, detail="Session Inactive / Expired")
    
    # Checking session fingerprint
    current_fingerprint_hash = generate_fingerprint(
        user_agent = request.headers.get("user-agent"),
        accept_language = request.headers.get("accept-language")
    )

    # Possible token theft - make session inactive
    if current_fingerprint_hash != session.fingerprint_hash:
        session.is_active = False
        token.revoked = True
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Device Mismatch. possible Token theft!!!"
        )
    
    # Same device so refresh existing token and issue access token
    token.revoked = True # marking the token as used one

    # Rotating refresh token
    # creating a new refresh token
    new_refresh_token = RefreshToken(
        session_id = token.session_id,
        token = create_refresh_token(),
        expires_at = refresh_token_expiry()
    )

    # updating the last used time
    session.last_used_at = datetime.now(timezone.utc)

    db.add(new_refresh_token)
    db.commit()

    access_token = create_access_token(session.user_id, session.id)

    # Extend session expiration in redis
    redis_client.expire(
        name=f"session:{session.id}",
        time=60 * 60 * 24 * 30
    )

    # setting new refresh token in cookies
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token.token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/"
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(
        request: Request,
        response: Response, 
        db: Session = Depends(get_db), 
        redis_client: Redis = Depends(get_redis_connection)
    ):

    # Get refresh token from cookies
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token: 
        raise HTTPException(status_code=401, detail="Missing Refresh token")

    # check if token is valid
    token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if not token:
        return {"message": "Already Logged Out!!!"}

    # check for active session for that token and mark it as inactive and revoke or delete token
    session = db.query(Sessions).filter(
        Sessions.id == token.session_id,
        Sessions.is_active == True
    ).first()

    # delete from redis
    redis_client.delete(f"session:{session.id}")   # instant logout

    if session:
        session.is_active = False

    token.revoked = True
    db.commit()

    # Delete cookie
    response.delete_cookie(
        key="refresh_token",
        path="/"
    )

    return {
        "message": "Logged Out Successfully"
    }

@router.post("/logout-all")
def logout_all(
        user_id: str = Depends(get_current_user_id), 
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_connection)
    ):
    
    # Mark all the session for that user as in active
    all_session = db.query(Sessions).filter(
        Sessions.user_id == user_id,
        Sessions.is_active == True
    ).all()

    for session in all_session:
        redis_client.delete(f"session:{session.id}")  # delete from redis
        session.is_active = False

    db.commit()

    return {"message" : "Logged Out of all devices!!!"}