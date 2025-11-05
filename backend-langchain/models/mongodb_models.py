from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema

# Chat message model
class ChatMessage(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    session_id: str
    user_id: int
    message: str
    response: str
    query_intent: Optional[str] = None
    generated_sql: Optional[str] = None
    query_results: Optional[List[Dict[str, Any]]] = None
    chart_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time: Optional[float] = None
    error: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Chat session model
class ChatSession(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    session_id: str
    user_id: int
    title: Optional[str] = "New Conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    is_active: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Query context model - stores conversation context for better query understanding
class QueryContext(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    session_id: str
    user_id: int
    context_summary: str  # Summary of conversation context
    key_entities: List[str] = []  # Extracted entities (customers, products, etc.)
    query_history: List[str] = []  # Recent query intents
    table_preferences: List[str] = []  # Tables user frequently queries
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}