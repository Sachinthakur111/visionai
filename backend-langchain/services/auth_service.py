import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt, ExpiredSignatureError
from dotenv import load_dotenv

from database.mysql_db import get_db
from models.mysql_models import User
from schemas.auth_schemas import UserInDB

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    print(f" Creating token with expiry: {expire} (ACCESS_TOKEN_EXPIRE_MINUTES = {ACCESS_TOKEN_EXPIRE_MINUTES})")
   
    
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def create_user(db: Session, username: str, email: str, password: str, role: str = "user") -> User:
    """Create new user"""
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        print(f"🔍 GET_CURRENT_USER - Verifying token: {token[:20]}...{token[-20:] if len(token) > 40 else token}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        
        # Manual expiry check
        from datetime import datetime
        exp_timestamp = payload.get("exp")
        current_timestamp = datetime.utcnow().timestamp()
        print(f" Token exp: {exp_timestamp}, Current: {current_timestamp}, Expired: {current_timestamp > exp_timestamp}")
        
        # Check if token is expired manually
        if exp_timestamp and current_timestamp > exp_timestamp:
            print("Token expired - Manual check")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except HTTPException:
        # Re-raise HTTP exceptions (including our manual expiry check)
        raise
    except ExpiredSignatureError:
        print("Token expired - ExpiredSignatureError caught")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception
    
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    
    return user

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token and return payload"""
    try:
        token = credentials.credentials
        print(f"🔍 VERIFY_TOKEN - Received token: {token[:20]}...{token[-20:] if len(token) > 40 else token}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        print(f"🎫 Token payload: {payload}")
        
        # Manual expiry check
        from datetime import datetime
        exp_timestamp = payload.get("exp")
        current_timestamp = datetime.utcnow().timestamp()
        print(f"🔐 Token exp: {exp_timestamp}, Current: {current_timestamp}, Expired: {current_timestamp > exp_timestamp}")
        
        # Check if token is expired manually
        if exp_timestamp and current_timestamp > exp_timestamp:
            print("Token expired - Manual check in verify_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username: str = payload.get("sub")
        if username is None:
            print(" No username in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        print(f"Token valid for user: {username}")
        return payload
    except HTTPException:
        # Re-raise HTTP exceptions (including our manual expiry check)
        raise
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )