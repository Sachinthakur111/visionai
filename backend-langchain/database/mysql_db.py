import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()

# Database configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "order_analytics")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")

# Database URL
DATABASE_URL = f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Create metadata instance
metadata = MetaData()

async def create_tables():
    """Create all tables in the database"""
    try:
        Base.metadata.create_all(bind=engine)
        print(" MySQL tables created successfully")
    except Exception as e:
        print(f" Error creating MySQL tables: {e}")

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_sync():
    """Get database session synchronously"""
    return SessionLocal()