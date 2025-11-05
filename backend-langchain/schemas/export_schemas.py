from pydantic import BaseModel
from typing import Dict, Any, Literal, Optional

class ExportRequest(BaseModel):
    format: Literal["excel", "pdf", "csv", "json"]
    data: Dict[str, Any]
    filename: Optional[str] = None

class ChartDataRequest(BaseModel):
    chart_type: str
    data: Dict[str, Any]

class ChartDataResponse(BaseModel):
    chart_data: Dict[str, Any]
    chart_config: Dict[str, Any]