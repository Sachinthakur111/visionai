from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Chat request schemas
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class NewSessionRequest(BaseModel):
    title: Optional[str] = "New Conversation"

# Chat response schemas - Standardized format
class ChatResponse(BaseModel):
    response: str
    session_id: str
    query_intent: Optional[str] = None
    display_type: Optional[str] = "text"  # CRITICAL: Display type for frontend rendering
    generated_sql: Optional[str] = None
    query_results: Optional[List[Dict[str, Any]]] = []
    chart_data: Optional[Dict[str, Any]] = None
    table_data: Optional[Dict[str, Any]] = None
    list_data: Optional[Dict[str, Any]] = None
    show_table: Optional[bool] = False  # Backward compatibility
    processing_time: Optional[float] = None
    followup_questions: Optional[List[str]] = None
    error: Optional[str] = None

class MessageHistory(BaseModel):
    message: str
    response: str
    timestamp: datetime
    query_intent: Optional[str] = None
    generated_sql: Optional[str] = None
    chart_data: Optional[Dict[str, Any]] = None

class SessionHistory(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    messages: List[MessageHistory]

class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    is_active: bool