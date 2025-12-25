from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from jose import JWTError
from redis import Redis

from app.auth.clients.redis import get_redis_connection
from app.auth.clients.database import get_db
from app.auth.models import User
from app.auth.utils.security.tokens import decode_access_token

# This is for swagger to know where to get token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user_id(
        token: str = Depends(oauth2_scheme), 
        db: Session = Depends(get_db),
        redis_client: Redis = Depends(get_redis_connection)
    ) -> str:
    try:
        payload = decode_access_token(token=token)

        # check for active session in redis
        session_id = payload["sid"]
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Missing Session"
            )
        
        if not redis_client.exists(f"session:{session_id}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Session Expired"
            )

        # check for valid user
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid User"
            )
        
        # user = db.get(User, user_id)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User does not exists"
            )
        
        return user_id

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token {e}"
        )