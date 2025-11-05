# schemas/response_schemas.py
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from enum import Enum

class DisplayType(str, Enum):
    TEXT = "text"
    LIST = "list"
    TABLE = "table"
    CHART_BAR = "chart_bar"
    CHART_LINE = "chart_line"
    CHART_PIE = "chart_pie"

class ChartData(BaseModel):
    type: str
    data: Dict[str, Any]
    title: Optional[str] = None

class TableData(BaseModel):
    type: str = "table"
    data: List[Dict[str, Any]]
    columns: List[str]
    total_rows: int
    title: Optional[str] = None

class ListData(BaseModel):
    type: str = "list"
    items: List[str]
    title: Optional[str] = None

class StandardizedChatResponse(BaseModel):
    """Standardized response format between backend and frontend"""
    response: str
    session_id: Optional[str] = None
    query_intent: str
    display_type: DisplayType
    generated_sql: Optional[str] = None
    query_results: Optional[List[Dict[str, Any]]] = []
    chart_data: Optional[ChartData] = None
    table_data: Optional[TableData] = None
    list_data: Optional[ListData] = None
    followup_questions: Optional[List[str]] = []
    processing_time: float
    error: Optional[str] = None

# Response templates for LLM formatting
RESPONSE_TEMPLATES = {
    "chart_bar": {
        "text_response": "Brief analysis of the bar chart data with key insights",
        "chart_data": {
            "type": "bar",
            "data": {
                "labels": ["Label1", "Label2", "Label3"],
                "datasets": [{
                    "label": "Dataset Name",
                    "data": [10, 20, 30],
                    "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56"]
                }]
            },
            "title": "Chart Title"
        },
        "table_data": None,
        "list_data": None
    },
    "chart_line": {
        "text_response": "Brief analysis of the line chart data with key insights",
        "chart_data": {
            "type": "line",
            "data": {
                "labels": ["Jan", "Feb", "Mar"],
                "datasets": [{
                    "label": "Dataset Name",
                    "data": [10, 20, 30],
                    "borderColor": "#36A2EB",
                    "fill": False
                }]
            },
            "title": "Chart Title"
        },
        "table_data": None,
        "list_data": None
    },
    "chart_pie": {
        "text_response": "Brief analysis of the pie chart data with key insights",
        "chart_data": {
            "type": "pie",
            "data": {
                "labels": ["Category1", "Category2", "Category3"],
                "datasets": [{
                    "data": [30, 50, 20],
                    "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56"]
                }]
            },
            "title": "Chart Title"
        },
        "table_data": None,
        "list_data": None
    },
    "table": {
        "text_response": "Brief analysis of the table data with key insights",
        "chart_data": None,
        "table_data": {
            "type": "table",
            "data": [{"col1": "value1", "col2": "value2"}],
            "columns": ["col1", "col2"],
            "total_rows": 100,
            "title": "Table Title"
        },
        "list_data": None
    },
    "list": {
        "text_response": "Brief analysis of the list data with key insights",
        "chart_data": None,
        "table_data": None,
        "list_data": {
            "type": "list",
            "items": ["item1", "item2", "item3"],
            "title": "List Title"
        }
    },
    "text": {
        "text_response": "Detailed text response with insights and analysis",
        "chart_data": None,
        "table_data": None,
        "list_data": None
    }
}

def get_response_template(display_type: str) -> Dict[str, Any]:
    """Get the appropriate response template for the given display type"""
    return RESPONSE_TEMPLATES.get(display_type, RESPONSE_TEMPLATES["text"])