from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from database.mysql_db import create_tables
from database.mongodb_db import init_mongodb
from routers import auth, chat, export
from services.auth_service import verify_token

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Order Analytics API...")
    try:
        print("Creating database tables...")
        await create_tables()
    except Exception as e:
        print(f"Database table creation failed: {e}")
        raise e
    try:
        print("Initializing MongoDB...")
        await init_mongodb()
    except Exception as e:
        print(f"MongoDB initialization failed: {e}")
        raise e
    print("✅ Server startup complete!")
    yield
    # Shutdown
    print("Shutting down Order Analytics API...")

app = FastAPI(
    title="Order Analytics System API",
    description="LangChain-powered analytics system with dynamic query generation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://172.20.7.52:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"], dependencies=[Depends(verify_token)])
app.include_router(export.router, prefix="/api/export", tags=["export"], dependencies=[Depends(verify_token)])

@app.get("/")
async def root():
    return {"message": "Order Analytics System API with LangChain", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "order-analytics-api"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )