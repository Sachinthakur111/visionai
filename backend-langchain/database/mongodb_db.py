import os
from dotenv import load_dotenv

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo.errors import ConnectionFailure
    MONGODB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MongoDB driver compatibility issue (Python 3.12): {e}")
    print("   Chat history will not be saved, but all analytics features will work normally")
    AsyncIOMotorClient = None
    ConnectionFailure = Exception
    MONGODB_AVAILABLE = False

load_dotenv()

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "chat_context")

# Global MongoDB client
mongodb_client: AsyncIOMotorClient = None
mongodb_database = None

async def init_mongodb():
    """Initialize MongoDB connection"""
    global mongodb_client, mongodb_database
    
    if not MONGODB_AVAILABLE:
        print("ℹ️ MongoDB driver not available - analytics will work, chat history disabled")
        return
    
    try:
        mongodb_client = AsyncIOMotorClient(MONGODB_URL)
        mongodb_database = mongodb_client[MONGODB_DATABASE]
        
        # Test connection
        await mongodb_client.admin.command('ping')
        print("✅ MongoDB connected successfully")
        
        # Create indexes for chat collections
        await create_indexes()
        
    except Exception as e:
        print(f"⚠️ MongoDB connection failed (optional): {e}")
        print("   Chat history will not be saved, but analytics will work")

async def create_indexes():
    """Create indexes for better performance"""
    try:
        # ONLY 2 collections for the simple chat system
        
        # Collection 1: chat_metadata - stores chat IDs and preview messages
        await mongodb_database.chat_metadata.create_index("user_id")
        await mongodb_database.chat_metadata.create_index("chat_id")
        await mongodb_database.chat_metadata.create_index([("user_id", 1), ("last_activity", -1)])
        await mongodb_database.chat_metadata.create_index([("user_id", 1), ("is_active", 1)])
        
        # Collection 2: chat_conversations - stores complete request/response dumps
        await mongodb_database.chat_conversations.create_index("user_id")
        await mongodb_database.chat_conversations.create_index("chat_id")
        await mongodb_database.chat_conversations.create_index([("chat_id", 1), ("timestamp", 1)])
        await mongodb_database.chat_conversations.create_index([("user_id", 1), ("timestamp", -1)])
        
        print("✅ MongoDB indexes created successfully for 2 collections: chat_metadata & chat_conversations")
    except Exception as e:
        print(f"⚠️ Warning: Could not create indexes: {e}")

async def close_mongodb():
    """Close MongoDB connection"""
    if mongodb_client:
        mongodb_client.close()
        print("📡 MongoDB connection closed")

def get_mongodb():
    """Get MongoDB database instance"""
    if not MONGODB_AVAILABLE:
        return None
    return mongodb_database