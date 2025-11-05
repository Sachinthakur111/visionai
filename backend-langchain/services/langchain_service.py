import os
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
# REMOVED: formatting_tools import - no longer needed with LLM-only approach
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import sqlalchemy as sa
from sqlalchemy.orm import Session
from database.mysql_db import get_db_sync, engine
import pandas as pd
import json
import re
from dotenv import load_dotenv
from schemas.response_schemas import StandardizedChatResponse, DisplayType, get_response_template

load_dotenv()

class LangChainQueryService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        # Initialize ChatOpenAI - Using GPT-4o-mini for speed with optimized prompts
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Fast model with better prompting
            temperature=0.1,
            max_tokens=1500,  # Increased for combined responses with data structures
            openai_api_key=self.openai_api_key
        )
        
        # Database schema information
        self.schema_info = self._get_schema_info()
    
    def _get_schema_info(self) -> str:
        """Get database schema information for the LLM"""
        return """
        DATABASE SCHEMA:
        
        Table: customers
        Columns:
        - id (INT, Primary Key): Unique customer identifier
        - customer_name (VARCHAR): Customer's full name
        - email (VARCHAR): Customer's email address
        - phone (VARCHAR): Customer's phone number
        - city (VARCHAR): Customer's city
        - state (VARCHAR): Customer's state
        - country (VARCHAR): Customer's country
        - customer_since (DATETIME): Date when customer joined
        - created_at (DATETIME): Record creation timestamp
        
        Table: orders
        Columns:
        - id (INT, Primary Key): Unique order identifier
        - order_number (VARCHAR): Human-readable order number
        - customer_id (INT, Foreign Key): References customers.id
        - order_date (DATETIME): Date when order was placed
        - total_amount (DECIMAL): Total order value
        - status (ENUM): Order status (pending, confirmed, shipped, delivered, cancelled, returned)
        - product_name (VARCHAR): Name of the product ordered
        - quantity (INT): Quantity of products ordered
        - unit_price (DECIMAL): Price per unit
        - category (VARCHAR): Product category
        - sales_rep (VARCHAR): Sales representative name
        - region (VARCHAR): Sales region
        - payment_method (VARCHAR): Payment method used
        - shipped_date (DATETIME): Date when order was shipped
        - delivered_date (DATETIME): Date when order was delivered
        - created_at (DATETIME): Record creation timestamp
        
        RELATIONSHIPS:
        - orders.customer_id -> customers.id (One customer can have many orders)
        """
    
    async def analyze_intent_and_generate_sql(self, user_query: str, conversation_context: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
        """
        OPTIMIZED: Combined intent analysis and SQL generation in single API call
        Returns: (intent_analysis, sql_query)
        """
        from datetime import datetime
        current_date = datetime.now()
        current_month = current_date.strftime("%Y-%m")
        current_year = current_date.year
        
        context_prompt = f"\nConversation Context: {conversation_context}" if conversation_context else ""
        
        print(f"DEBUG - Date Context: Today={current_date.strftime('%Y-%m-%d')}, Month={current_month}, Year={current_year}")
        
        combined_prompt = f"""
        You are an AI assistant for business analytics. Perform TWO tasks in sequence:
        
        CURRENT DATE CONTEXT:
        - Today's date: {current_date.strftime("%Y-%m-%d")}
        - Current month: {current_month} 
        - Current year: {current_year}
        - When user says "this month" use: {current_month}-01 to {current_month}-31
        - When user says "this year" use: {current_year}-01-01 to {current_year}-12-31
        - When user says "last month" use previous month dates
        - Always use CURRENT YEAR {current_year} unless explicitly mentioned otherwise
        
        EXAMPLES:
        - "total revenue this month" → WHERE MONTH(order_date) = {current_date.month} AND YEAR(order_date) = {current_year}
        - "sales this year" → WHERE YEAR(order_date) = {current_year}
        - "revenue in September" → WHERE MONTH(order_date) = 9 AND YEAR(order_date) = {current_year}
        
        {self.schema_info}
        
        TASK 1: Analyze user intent and determine:
        1. Primary intent and sub-intent
        2. Required data points and filters
        3. Display type needed (text/list/table/chart_bar/chart_line/chart_pie)
        4. Tables and complexity
        
        TASK 2: Generate MySQL query based on the intent analysis
        
        User Query: "{user_query}"{context_prompt}
        
        Respond in this EXACT JSON format:
        {{
            "intent_analysis": {{
                "intent": "primary_intent_category",
                "sub_intent": "specific_intent_description", 
                "data_points": ["list", "of", "required", "data"],
                "filters": {{"column": "condition"}},
                "time_range": {{"start": "date", "end": "date"}} or null,
                "grouping": ["columns", "to", "group", "by"],
                "aggregations": ["sum", "count", "avg"],
                "display_type": "text|list|table|chart_bar|chart_line|chart_pie",
                "tables_needed": ["customers", "orders"],
                "complexity": "simple|medium|complex"
            }},
            "sql_query": "SELECT ... FROM ... WHERE ... ORDER BY ... LIMIT ..."
        }}
        
        DISPLAY TYPE GUIDELINES:
        - "text": Simple answers, single values, explanations
        - "list": Multiple items, bullet points, short lists  
        - "table": Detailed data with multiple columns, raw data
        - "chart_bar": Comparisons, rankings, categorical data
        - "chart_line": Trends over time, time series data
        - "chart_pie": Proportions, percentages, parts of a whole
        
        SQL RULES:
        - Use proper table aliases (c for customers, o for orders)
        - Include proper JOINs when needed
        - Use appropriate WHERE clauses for filters
        - Include GROUP BY and aggregations as needed
        - CRITICAL: When user requests sorting/ordering, ALWAYS include ORDER BY clause (e.g., "sorted by price" → ORDER BY total_amount DESC)
        - Order results meaningfully and use LIMIT
        - Ensure syntactically correct MySQL
        - CRITICAL: Use CURRENT YEAR {current_year} for date filters unless user specifies otherwise
        - For "this month" queries, use MONTH(o.order_date) = {current_date.month} AND YEAR(o.order_date) = {current_year}
        - For date ranges, always consider current context: {current_date.strftime("%Y-%m-%d")}
        """
        
        try:
            messages = [
                SystemMessage(content="You are a business analytics assistant. Analyze intent and generate SQL in a single response. Always respond with valid JSON."),
                HumanMessage(content=combined_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Clean up the response to extract JSON
            response_text = response.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            combined_response = json.loads(response_text)
            
            intent_analysis = combined_response.get('intent_analysis', {})
            sql_query = combined_response.get('sql_query', '')
            
            # Clean up SQL query
            sql_query = re.sub(r'^```sql\s*', '', sql_query)
            sql_query = re.sub(r'\s*```$', '', sql_query)
            sql_query = sql_query.strip()
            
            return intent_analysis, sql_query
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error in combined analysis: {e}")
            print(f"Raw response: {response_text[:200] if 'response_text' in locals() else 'No response'}")
            
            # Fallback intent and SQL
            fallback_intent = {
                "intent": "general_query",
                "sub_intent": "Unable to parse LLM response",
                "data_points": [],
                "filters": {},
                "time_range": None,
                "grouping": [],
                "aggregations": [],
                "display_type": "table",
                "tables_needed": ["orders", "customers"],
                "complexity": "medium"
            }
            fallback_sql = "SELECT o.*, c.customer_name FROM orders o JOIN customers c ON o.customer_id = c.id ORDER BY o.order_date DESC LIMIT 10;"
            
            return fallback_intent, fallback_sql
            
        except Exception as e:
            print(f"Error in combined analysis: {e}")
            
            # Fallback intent and SQL
            fallback_intent = {
                "intent": "general_query",
                "sub_intent": "Unable to determine specific intent",
                "data_points": [],
                "filters": {},
                "time_range": None,
                "grouping": [],
                "aggregations": [],
                "display_type": "table",
                "tables_needed": ["orders", "customers"],
                "complexity": "medium"
            }
            fallback_sql = "SELECT o.*, c.customer_name FROM orders o JOIN customers c ON o.customer_id = c.id ORDER BY o.order_date DESC LIMIT 10;"
            
            return fallback_intent, fallback_sql
    
    # REMOVED: generate_sql_query method - now combined with intent analysis
    
    def execute_sql_query(self, sql_query: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Third step: Execute the SQL query and return results
        """
        try:
            # Execute query using pandas for better data handling
            df = pd.read_sql_query(sql_query, engine)
            
            # Convert to list of dictionaries
            results = df.to_dict('records')
            
            # Handle datetime objects and other non-serializable types
            for row in results:
                for key, value in row.items():
                    if pd.isna(value):
                        row[key] = None
                    elif isinstance(value, pd.Timestamp):
                        row[key] = value.isoformat()
                    elif isinstance(value, (pd.Int64Dtype, pd.Float64Dtype)):
                        row[key] = value.item() if hasattr(value, 'item') else value
            
            return results, None
            
        except Exception as e:
            error_msg = str(e)
            print(f"SQL Execution Error: {error_msg}")
            return [], error_msg
    
    async def format_complete_response(self, 
                                     user_query: str, 
                                     intent_analysis: Dict[str, Any], 
                                     sql_query: str, 
                                     query_results: List[Dict[str, Any]], 
                                     error: Optional[str] = None) -> Dict[str, Any]:
        """
        OPTIMIZED: Complete response formatting with standardized templates
        """
        if error:
            return {
                "response": f"I encountered an error while processing your query: {error}. Please try rephrasing your question or check if the data you're looking for exists.",
                "chart_data": None,
                "table_data": None,
                "list_data": None
            }
        
        # Handle context-based queries that don't need data
        is_context_query = (
            intent_analysis.get('intent') in ['explanation', 'clarification', 'followup'] or
            len(intent_analysis.get('tables_needed', [])) == 0
        )
        
        if not query_results and not is_context_query:
            return {
                "response": "I didn't find any data matching your query. This could mean there are no records that match your criteria, or the query might need to be adjusted.",
                "chart_data": None,
                "table_data": None,
                "list_data": None
            }
        
        display_type = intent_analysis.get('display_type', 'text')
        
        # Get standardized template for the display type
        response_template = get_response_template(display_type)
        
        # Create comprehensive prompt with standardized template
        data_info = f"DATA ({len(query_results)} records): {json.dumps(query_results[:10], default=str)}" if query_results else "NO DATA NEEDED - This is a context-based explanation query"
        
        complete_prompt = f"""
        You are a business analytics assistant. Generate a complete response with both text and data structures.
        
        USER QUERY: "{user_query}"
        INTENT ANALYSIS: {json.dumps(intent_analysis, default=str)}
        DISPLAY TYPE: {display_type}
        {data_info}
        IS_CONTEXT_QUERY: {is_context_query}
        
        Use this EXACT template and replace with actual data:
        {json.dumps(response_template, indent=2)}
        
        CRITICAL FORMATTING RULES:
        {"- CONTEXT QUERIES: If IS_CONTEXT_QUERY is True, focus on explanation and set all data structures (chart_data, table_data, list_data) to null" if is_context_query else ""}
        - For display_type "{display_type}": Generate the corresponding data structure with REAL data from query results
        - Chart data must be Chart.js compatible with proper labels and datasets
        - Table data should include actual columns and rows from query_results
        - List data should be meaningful representations of the data
        - Always use actual values from the query results, not placeholder data
        - Ensure JSON is valid and properly formatted
        - If you cannot generate the required format, set the data structure to null
        
        STRICT DATA STRUCTURE REQUIREMENTS:
        - chart_data MUST be a dictionary with "type", "data", "title" keys OR null
        - table_data MUST be a dictionary with "type", "data", "columns", "total_rows", "title" keys OR null  
        - list_data MUST be a dictionary with "type", "items", "title" keys OR null
        - NEVER return arrays/lists directly for these fields
        
        TEXT RESPONSE GUIDELINES:
        {"- CONTEXT QUERIES: Provide explanations, clarifications, or insights based on conversation context" if is_context_query else "- Analyze the actual data provided"}
        {"- Use your knowledge to explain concepts, interpret previous results, or provide guidance" if is_context_query else "- Provide specific insights with real numbers"}
        - Keep response concise (2-3 sentences)
        - Focus on business value and trends
        
        IMPORTANT: Return ONLY the JSON response, no additional text or markdown.
        VALIDATE: Ensure your JSON structure exactly matches the template format.
        """
        
        try:
            messages = [
                SystemMessage(content="You are a business analytics assistant. Generate complete responses with text and structured data. Always respond with valid JSON."),
                HumanMessage(content=complete_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Clean up the response to extract JSON
            response_text = response.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            complete_response = json.loads(response_text)
            
            # Validate and fix data structures
            chart_data = complete_response.get('chart_data')
            table_data = complete_response.get('table_data')  
            list_data = complete_response.get('list_data')
            
            # Fix list_data if it's incorrectly formatted
            if list_data and isinstance(list_data, list):
                # Convert list to proper format
                list_data = {
                    "type": "list",
                    "items": [str(item) if isinstance(item, dict) else item for item in list_data[:10]],
                    "title": "Data List"
                }
            elif list_data and not isinstance(list_data, dict):
                list_data = None
                
            # Fix table_data if it's incorrectly formatted  
            if table_data and isinstance(table_data, list):
                # Convert list to proper table format
                if table_data:
                    table_data = {
                        "type": "table",
                        "data": table_data,
                        "columns": list(table_data[0].keys()) if table_data else [],
                        "total_rows": len(table_data),
                        "title": "Data Table"
                    }
                else:
                    table_data = None
            elif table_data and not isinstance(table_data, dict):
                table_data = None
                
            # Fix chart_data if it's incorrectly formatted
            if chart_data and not isinstance(chart_data, dict):
                chart_data = None
            
            return {
                "response": complete_response.get('text_response', 'Analysis completed successfully.'),
                "chart_data": chart_data,
                "table_data": table_data,
                "list_data": list_data
            }
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error in complete formatting: {e}")
            print(f"Raw response: {response_text[:200] if 'response_text' in locals() else 'No response'}")
            
            # Fallback response
            return {
                "response": f"I found {len(query_results)} records matching your query. Here's a summary of the key findings from your data.",
                "chart_data": None,
                "table_data": None,
                "list_data": None
            }
            
        except Exception as e:
            print(f"Error in complete formatting: {e}")
            
            # Fallback response
            return {
                "response": f"I found {len(query_results)} records matching your query. Here's a summary of the key findings from your data.",
                "chart_data": None,
                "table_data": None,
                "list_data": None
            }
    
    # REMOVED: generate_formatted_data method - now handled by LLM in format_complete_response
    
    async def process_user_query(self, 
                               user_query: str, 
                               conversation_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method that orchestrates the entire query processing pipeline
        """
        start_time = time.time()
        
        try:
            # OPTIMIZED STEP 1: Combined intent analysis and SQL generation (1 API call)
            intent_analysis, sql_query = await self.analyze_intent_and_generate_sql(user_query, conversation_context)
            
            # Check if this is a context-based query that doesn't need SQL execution
            needs_sql = (
                sql_query and sql_query.strip() and 
                intent_analysis.get('tables_needed') and 
                len(intent_analysis.get('tables_needed', [])) > 0 and
                intent_analysis.get('intent') not in ['explanation', 'clarification', 'followup']
            )
            
            if needs_sql:
                # STEP 2: Execute SQL query (local)
                query_results, error = self.execute_sql_query(sql_query)
            else:
                # Handle context-based queries without SQL
                print(f"DEBUG - Skipping SQL execution for context-based query. Intent: {intent_analysis.get('intent')}")
                query_results, error = [], None
                if not sql_query or not sql_query.strip():
                    sql_query = "-- No SQL query needed for this explanation/context-based response"
            
            # OPTIMIZED STEP 3: Complete response formatting with data structures (1 API call)
            complete_formatting = await self.format_complete_response(user_query, intent_analysis, sql_query, query_results, error)
            
            processing_time = time.time() - start_time
            
            # Get LLM-determined display type
            display_type = intent_analysis.get('display_type', 'text')
            
            # Debug logging
            print(f"DEBUG - Intent Analysis: {intent_analysis}")
            print(f"DEBUG - Display Type: {display_type}")
            print(f"DEBUG - Complete Formatting: {complete_formatting}")
            
            # Ensure standardized response format
            standardized_response = {
                "response": complete_formatting.get("text_response") or complete_formatting.get("response", "Analysis completed."),
                "session_id": None,  # Will be set by API route
                "query_intent": intent_analysis.get('sub_intent', 'General query'),
                "display_type": display_type,
                "generated_sql": sql_query,
                "query_results": query_results[:100],  # Limit to 100 records for response
                "chart_data": complete_formatting.get("chart_data"),     # LLM-formatted chart data
                "table_data": complete_formatting.get("table_data"),     # LLM-formatted table data  
                "list_data": complete_formatting.get("list_data"),       # LLM-formatted list data
                "followup_questions": None,  # Let Chat service generate dynamic questions
                "processing_time": processing_time,
                "error": error
            }
            
            print(f"DEBUG - Final Response: {standardized_response}")
            return standardized_response
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"An unexpected error occurred: {str(e)}"
            
            return {
                "response": "I apologize, but I encountered an error while processing your query. Please try asking your question in a different way.",
                "query_intent": "error",
                "display_type": "text",
                "generated_sql": None,
                "query_results": [],
                "chart_data": None,
                "table_data": None,
                "list_data": None,
                "processing_time": processing_time,
                "error": error_msg
            }
