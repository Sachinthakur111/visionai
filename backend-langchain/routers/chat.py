from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from schemas.chat_schemas import (
    ChatRequest, 
    ChatResponse, 
    NewSessionRequest, 
    SessionHistory, 
    SessionInfo
)
from services.auth_service import get_current_user
from services.chat_service import ChatService

router = APIRouter()

# Initialize chat service
chat_service = ChatService()

@router.post("/", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user = Depends(get_current_user)
):
    """Process a chat message and return AI response"""
    try:
        result = await chat_service.process_message(
            user_id=current_user.id,
            message=chat_request.message,
            session_id=chat_request.session_id
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )

@router.post("/new-session")
async def create_new_session(
    session_request: Optional[NewSessionRequest] = None,
    current_user = Depends(get_current_user)
):
    """Create a new chat session"""
    try:
        # Handle case where no request body is sent
        title = session_request.title if session_request else "New Conversation"
        
        # Create session in database immediately
        session_id = await chat_service.create_new_session(current_user.id, title)
        
        return {"session_id": session_id, "title": title}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )

@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get chat history for a specific session"""
    try:
        messages = await chat_service.get_chat_history(session_id, current_user.id)
        
        # Return a basic response even if MongoDB is not available
        return {
            "session_id": session_id,
            "title": "Chat Session",
            "created_at": None,
            "last_activity": None,
            "message_count": len(messages),
            "messages": messages
        }
        
    except Exception as e:
        # Return empty history instead of error
        print(f"Error retrieving history: {e}")
        return {
            "session_id": session_id,
            "title": "Chat Session", 
            "created_at": None,
            "last_activity": None,
            "message_count": 0,
            "messages": []
        }

@router.get("/sessions")
async def get_user_sessions(
    current_user = Depends(get_current_user)
):
    """Get all sessions for the current user"""
    try:
        sessions = await chat_service.get_user_sessions(current_user.id)
        return {"sessions": sessions}
        
    except Exception as e:
        # Return empty sessions instead of error
        print(f"Error retrieving sessions: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {"sessions": []}

@router.delete("/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Clear/delete a chat session"""
    try:
        # Try to delete the session (handles both existing and non-existing sessions)
        success = await chat_service.delete_session(session_id, current_user.id)
        
        # Always return success - if session doesn't exist, it's effectively "deleted"
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        )