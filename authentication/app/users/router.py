from fastapi import APIRouter, Depends
from app.auth.jwt_dependency import get_current_user_id

router = APIRouter(prefix="/user", tags=["user"])

@router.get("")
def read_me(user_id: int = Depends(get_current_user_id)):
    return {
        "user_id" : user_id,
        "message" : "You are authenticated"
    }