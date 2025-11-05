from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models.mysql_models import UserRole

# Request schemas
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.USER

# Response schemas
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class UserInDB(UserResponse):
    password_hash: str