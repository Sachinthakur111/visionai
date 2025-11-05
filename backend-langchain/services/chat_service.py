# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from database.mongodb_db import get_mongodb
from models.mongodb_models import ChatMessage, ChatSession, QueryContext
from services.langchain_service import LangChainQueryService

class ChatService:
    def __init__(self):
        self.langchain_service = LangChainQueryService()
    
    @property
    def mongodb(self):
        """Get MongoDB connection dynamically"""
        return get_mongodb()
    
    @property 
    def mongodb_available(self):
        """Check if MongoDB is available dynamically"""
        mongodb_db = self.mongodb
        return mongodb_db is not None
    
    async def create_new_session(self, user_id: int, title: Optional[str] = None) -> str:
        """Create a new chat session and return session_id"""
        session_id = str(uuid.uuid4())
        
        if self.mongodb_available:
            try:
                session_doc = {
                    "chat_id": session_id,
                    "user_id": user_id,
                    "title": title or "New Chat",
                    "preview_message": None,
                    "created_at": datetime.utcnow(),
                    "last_activity": datetime.utcnow(),
                    "message_count": 0,
                    "is_active": True
                }
                
                # Collection 1: chat_metadata - stores chat ID and preview
                result = await self.mongodb.chat_metadata.insert_one(session_doc)
                print(f"Session {session_id} created in chat_metadata with _id: {result.inserted_id}")
                print(f"Session document: {session_doc}")
            except Exception as e:
                print(f"Failed to save session to MongoDB: {e}")
                import traceback
                print(f"   Full traceback: {traceback.format_exc()}")
        
        return session_id
    
    async def get_conversation_context(self, session_id: str, user_id: int) -> Optional[str]:
        """Get recent conversation context for the session"""
        if not self.mongodb_available:
            print("MongoDB not available - no conversation context")
            return None
            
        try:
            # Get recent conversations from this session
            recent_conversations = await self.mongodb.chat_conversations.find({
                "chat_id": session_id,
                "user_id": user_id
            }).sort("timestamp", -1).limit(5).to_list(5)
            
            if not recent_conversations:
                return None
            
            # Build context string from recent conversations
            context_parts = []
            for conv in reversed(recent_conversations):  # Reverse to get chronological order
                user_message = conv.get('user_message')
                assistant_response = conv.get('assistant_response', {}).get('response', '')
                
                if user_message:
                    context_parts.append(f"User: {user_message}")
                if assistant_response:
                    context_parts.append(f"Assistant: {assistant_response[:200]}...")
            
            return "\n".join(context_parts[-10:])  # Limit context size
            
        except Exception as e:
            print(f"Error getting conversation context: {e}")
            return None
    
    async def get_session_info(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get session information from chat_metadata collection"""
        if not self.mongodb_available:
            return {"session_id": session_id, "title": "Chat Session", "created_at": datetime.utcnow()}
        
        try:
            session = await self.mongodb.chat_metadata.find_one({
                "chat_id": session_id,
                "user_id": user_id
            })
            return session
        except Exception as e:
            print(f"Failed to get session info: {e}")
            return {"session_id": session_id, "title": "Chat Session", "created_at": datetime.utcnow()}
    
    async def process_message(self, user_id: int, message: str, session_id: Optional[str] = None,
                              create_if_missing: bool = False) -> Dict[str, Any]:
        """
        Process a user message and generate response.
        If session_id is missing:
          - try to reuse the user's most recent active session (if any)
          - if none found, only create a new session when create_if_missing=True
        """
        
        print(f"🎯 Processing message from user {user_id}: {message}")
        print(f"LOG: incoming session_id={session_id} create_if_missing={create_if_missing}")

        # --- Resolve session_id safely ---
        if not session_id:
            # Try to find last active session for this user
            if self.mongodb_available:
                try:
                    last = await self.mongodb.chat_metadata.find_one(
                        {"user_id": user_id, "is_active": True},
                        sort=[("last_activity", -1)]
                    )
                    if last:
                        session_id = last.get("chat_id")
                        print(f" Found existing session for user {user_id}: {session_id}")
                except Exception as e:
                    print(f" Error while looking up last session: {e}")
            
            # If still missing, create only if allowed
            if not session_id and create_if_missing:
                session_id = await self.create_new_session(user_id, "Auto-created Session")
                print(f"Created fallback session: {session_id}")
            elif not session_id:
                # No session and not allowed to create — return error-like response
                print(" No session_id provided and creation not allowed. Aborting.")
                return {
                    "error": "no_session",
                    "message": "Session not found. Create a new chat or provide session_id."
                }
        else:
            print(f" Using session: {session_id}")
        
        # Get conversation context
        print("🔍 Getting conversation context...")
        conversation_context = await self.get_conversation_context(session_id, user_id)
        
        # Process the query using LangChain
        print("🤖 Processing query with LangChain...")
        result = await self.langchain_service.process_user_query(message, conversation_context)
        print(f" LangChain processing complete. Response: {result['response'][:100]}...")
        
        # Generate follow-up questions
        followup_questions = await self.generate_followup_questions(
            user_query=message,
            query_intent=result['query_intent'], 
            query_results=result.get('query_results', []),
            conversation_context=conversation_context
        )
        
        # Build the complete response structure that will be sent to frontend
        complete_response = {
            "response": result['response'],
            "session_id": session_id,
            "query_intent": result['query_intent'],
            "display_type": result.get('display_type', 'text'),
            "generated_sql": result.get('generated_sql'),
            "query_results": result.get('query_results', []),
            "chart_data": result.get('chart_data'),
            "table_data": result.get('table_data'),
            "list_data": result.get('list_data'),
            "show_table": result.get('display_type') == 'table',
            "processing_time": result.get('processing_time'),
            "followup_questions": followup_questions,
            "error": result.get('error')
        }
        
        # Save to MongoDB - EXACTLY what we're sending to frontend
        if self.mongodb_available:
            try:
                # Collection 2: chat_conversations - Store complete request/response
                conversation_record = {
                    "chat_id": session_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow(),
                    "user_message": message,
                    "assistant_response": complete_response  # Save EXACT response sent to frontend
                }
                
                await self.mongodb.chat_conversations.insert_one(conversation_record)
                print(f" Complete conversation saved to chat_conversations for session {session_id}")
                
                # Collection 1: chat_metadata - Update metadata
                metadata_doc = await self.mongodb.chat_metadata.find_one({
                    "chat_id": session_id, "user_id": user_id
                })
                
                update_data = {
                    "$set": {
                        "last_activity": datetime.utcnow(),
                    },
                    "$inc": {"message_count": 1}
                }
                
                # If this is first message, set as preview
                if metadata_doc and metadata_doc.get('message_count', 0) == 0:
                    preview = message[:50] + "..." if len(message) > 50 else message
                    update_data["$set"]["preview_message"] = preview
                    print(f"📝 Setting preview message: {preview}")
                
                await self.mongodb.chat_metadata.update_one(
                    {"chat_id": session_id, "user_id": user_id},
                    update_data
                )
                print(f"Chat metadata updated")
                
            except Exception as e:
                print(f"Failed to save chat to MongoDB: {e}")
                import traceback
                print(f"   Full traceback: {traceback.format_exc()}")
        
        # Return the exact same response structure
        return complete_response
    
    async def get_chat_history(self, session_id: str, user_id: int) -> List[Dict[str, Any]]:
        """Get complete chat history for a specific session from chat_conversations collection"""
        if not self.mongodb_available:
            print(f" MongoDB not available for chat history {session_id}")
            return []
            
        try:
            print(f"🔍 Loading chat history for session {session_id}, user {user_id}")
            
            # Get all conversations for this session, sorted by timestamp
            conversations = await self.mongodb.chat_conversations.find({
                "chat_id": session_id,
                "user_id": user_id
            }).sort("timestamp", 1).to_list(None)
            
            print(f"📚 Found {len(conversations)} conversations in database")
            
            if not conversations:
                print(f" No conversations found for session {session_id}")
                return []
            
            # Format messages for frontend - return EXACTLY what was saved
            formatted_messages = []
            for conv in conversations:
                # Add user message
                formatted_messages.append({
                    "id": f"{conv['_id']}_user",
                    "content": conv.get('user_message', ''),
                    "role": "user",
                    "timestamp": conv.get('timestamp', datetime.utcnow()).isoformat(),
                })
                
                # Add assistant response - EXACTLY as it was saved
                assistant_response = conv.get('assistant_response', {})
                formatted_messages.append({
                    "id": f"{conv['_id']}_assistant",
                    "content": assistant_response.get('response', ''),
                    "role": "assistant",
                    "timestamp": conv.get('timestamp', datetime.utcnow()).isoformat(),
                    # Include ALL the fields that were saved
                    "queryExecuted": assistant_response.get('generated_sql'),
                    "displayType": assistant_response.get('display_type', 'text'),
                    "chartData": assistant_response.get('chart_data'),
                    "chartType": assistant_response.get('chart_data', {}).get('type') if assistant_response.get('chart_data') else None,
                    "tableData": assistant_response.get('table_data'),
                    "listData": assistant_response.get('list_data'),
                    "followUpQuestions": assistant_response.get('followup_questions', []),
                    "showTable": assistant_response.get('show_table', False),
                    "error": assistant_response.get('error')
                })
            
            print(f"Formatted {len(formatted_messages)} messages for frontend")
            return formatted_messages
            
        except Exception as e:
            print(f"Error getting chat history: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return []
    
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user from chat_metadata collection"""
        
        if not self.mongodb_available:
            return []
            
        try:
            # Get all active sessions for this user
            sessions = await self.mongodb.chat_metadata.find({
                "user_id": user_id,
                "is_active": True
            }).sort("last_activity", -1).to_list(None)
            
            # Format sessions for frontend
            formatted_sessions = []
            for session in sessions:
                message_count = session.get('message_count', 0)
                preview_msg = session.get('preview_message', '')
                title = session.get('title', 'New Chat')
                
                # SKIP SESSIONS WITHOUT ANY MESSAGES
                if message_count == 0 or not preview_msg:
                    continue
                
                # Use title if set, otherwise use preview, otherwise default
                display_title = title if title != 'New Chat' else (preview_msg if preview_msg else 'New Chat')
                display_preview = preview_msg if preview_msg else 'No messages yet'
                
                formatted_sessions.append({
                    "session_id": session['chat_id'],
                    "title": display_title,
                    "created_at": session.get('created_at', datetime.utcnow()).isoformat(),
                    "last_activity": session.get('last_activity', datetime.utcnow()).isoformat(),
                    "message_count": message_count,
                    "preview": display_preview
                })
            
            return formatted_sessions
            
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return []
    
    async def delete_session(self, session_id: str, user_id: int) -> bool:
        """Delete a chat session and all its messages from collections"""
        if not self.mongodb_available:
            return True  # Assume success if no MongoDB
            
        try:
            # Delete all conversations for this session from chat_conversations
            result1 = await self.mongodb.chat_conversations.delete_many({
                "chat_id": session_id,
                "user_id": user_id
            })
            print(f"🗑️ Deleted {result1.deleted_count} conversations from chat_conversations")
            
            # Mark session as inactive in chat_metadata (soft delete)
            result2 = await self.mongodb.chat_metadata.delete_one(
                {
                    "chat_id": session_id,
                    "user_id": user_id
                }
            )


            print(f"🗑️ Marked session as inactive in chat_metadata")
            
            print(f" Session {session_id} deleted successfully")
            return True
            
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    async def generate_followup_questions(self, user_query: str, query_intent: str, 
                                         query_results: List[Dict[str, Any]], 
                                         conversation_context: Optional[str] = None) -> List[str]:
        """Generate intelligent follow-up questions using LLM based on context and results"""
        
        try:
            # Prepare data summary for LLM context
            results_summary = {
                "total_records": len(query_results),
                "sample_data": query_results[:3] if query_results else [],
                "columns": list(query_results[0].keys()) if query_results else []
            }
            
            # Create follow-up generation prompt
            followup_prompt = f"""
            You are an expert business analyst generating intelligent follow-up questions.
            
            CONTEXT:
            - User just asked: "{user_query}"
            - Query intent: {query_intent}
            - Found {results_summary['total_records']} records with columns: {results_summary['columns']}
            - Sample data: {results_summary['sample_data']}
            - Previous conversation: {conversation_context or 'None'}
            
            Generate EXACTLY 3 intelligent follow-up questions that:
            1. Build naturally on what the user just learned
            2. Explore different dimensions of the same data
            3. Suggest deeper analysis or related insights
            4. Are specific and actionable (not generic)
            5. Consider the conversation history to avoid repetition
            
            RULES:
            - Each question should be 8-15 words max
            - Make questions specific to the actual data found
            - Avoid generic questions like "show me analytics" 
            - Focus on business insights the user might want next
            - Consider drill-down, comparison, and trend analysis
            
            Return ONLY 3 questions, one per line, no numbering or bullets:
            """
            
            # Import LangChain components  
            import os
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage
            
            # Initialize LLM for follow-up questions
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=150,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            messages = [
                SystemMessage(content="You are a business analytics expert who generates intelligent follow-up questions."),
                HumanMessage(content=followup_prompt)
            ]
            
            response = await llm.ainvoke(messages)
            
            # Parse the response into individual questions
            questions = [q.strip() for q in response.content.split('\n') if q.strip()]
            
            # Ensure we have exactly 3 questions
            if len(questions) < 3:
                # Add context-aware backup questions
                backup_questions = self._generate_backup_questions(results_summary['columns'], query_intent)
                questions.extend(backup_questions[:3-len(questions)])
            
            return questions[:3]
            
        except Exception as e:
            print(f"Error generating AI follow-up questions: {e}")
            # Fallback to context-aware static questions
            return self._generate_backup_questions(
                list(query_results[0].keys()) if query_results else [], 
                query_intent
            )[:3]
    
    def _generate_backup_questions(self, columns: List[str], query_intent: str) -> List[str]:
        """Generate backup follow-up questions based on available data columns"""
        questions = []
        
        # Column-based suggestions
        if any(col for col in columns if 'date' in col.lower() or 'time' in col.lower()):
            questions.append("Show me trends over time")
        
        if any(col for col in columns if 'status' in col.lower()):
            questions.append("What's the status distribution?")
            
        if any(col for col in columns if 'amount' in col.lower() or 'price' in col.lower() or 'revenue' in col.lower()):
            questions.append("How do amounts compare across categories?")
            
        if any(col for col in columns if 'customer' in col.lower()):
            questions.append("Which customers are most active?")
            
        if any(col for col in columns if 'product' in col.lower()):
            questions.append("What are the top performing products?")
        
        # Intent-based fallbacks
        if "customer" in query_intent.lower():
            questions.extend(["Show customer lifetime value", "What's the retention rate?"])
        elif "product" in query_intent.lower():
            questions.extend(["Compare product performance", "Show seasonal trends"])
        elif "order" in query_intent.lower():
            questions.extend(["Analyze order patterns", "Show delivery performance"])
        
        # Generic fallbacks
        questions.extend([
            "Show me regional performance",
            "What are the key business metrics?",
            "How do recent trends look?"
        ])
        
        return questions
