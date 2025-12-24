from pydantic import BaseModel, EmailStr

class CreateUser(BaseModel):
    email: EmailStr
    name: str
    password: str
