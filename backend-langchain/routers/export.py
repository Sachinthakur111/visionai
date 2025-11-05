from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from io import BytesIO

from schemas.export_schemas import ExportRequest, ChartDataRequest, ChartDataResponse
from services.auth_service import get_current_user
from services.export_service import ExportService

router = APIRouter()

# Initialize export service
export_service = ExportService()

@router.post("/")
async def export_data(
    export_request: ExportRequest,
    current_user = Depends(get_current_user)
):
    """Export data in specified format"""
    try:
        data = export_request.data.get("data", [])
        filename = export_request.filename or f"export_{export_request.format}"
        
        if export_request.format == "excel":
            content = export_service.export_to_excel(data, filename)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{filename}.xlsx"
            
        elif export_request.format == "csv":
            content = export_service.export_to_csv(data, filename)
            media_type = "text/csv"
            filename = f"{filename}.csv"
            
        elif export_request.format == "json":
            content = export_service.export_to_json(data, filename)
            media_type = "application/json"
            filename = f"{filename}.json"
            
        elif export_request.format == "pdf":
            content = export_service.export_to_pdf(data, filename)
            media_type = "application/pdf"
            filename = f"{filename}.pdf"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {export_request.format}"
            )
        
        # Create streaming response
        buffer = BytesIO(content)
        
        return StreamingResponse(
            BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting data: {str(e)}"
        )

@router.post("/chart-data", response_model=ChartDataResponse)
async def generate_chart_data(
    chart_request: ChartDataRequest,
    current_user = Depends(get_current_user)
):
    """Generate chart configuration data"""
    try:
        data = chart_request.data.get("data", [])
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for chart generation"
            )
        
        chart_data = export_service.generate_chart_data(
            chart_type=chart_request.chart_type,
            data=data
        )
        
        if "error" in chart_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=chart_data["error"]
            )
        
        return ChartDataResponse(
            chart_data=chart_data,
            chart_config={
                "type": chart_request.chart_type,
                "responsive": True,
                "maintainAspectRatio": False
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating chart data: {str(e)}"
        )