"""
Formatting Tools for Hybrid LLM + Tools Architecture
These tools handle data formatting based on LLM-determined display_type
"""
from typing import Dict, Any, List, Optional, Tuple
import json


class ChartFormatterTool:
    """Tool for formatting data into chart-ready format"""
    
    @staticmethod
    def format_chart_data(query_results: List[Dict[str, Any]], display_type: str) -> Optional[Dict[str, Any]]:
        """
        Format query results into chart data based on display_type
        
        Args:
            query_results: Raw SQL query results
            display_type: LLM-determined display type (chart_bar, chart_line, chart_pie)
            
        Returns:
            Formatted chart data or None if not applicable
        """
        if not display_type.startswith('chart_') or not query_results:
            return None
            
        try:
            # Extract chart type (e.g., "chart_bar" -> "bar")
            chart_type = display_type.replace('chart_', '')
            
            # Generic data structure analysis
            if not query_results or len(query_results[0].keys()) < 2:
                return None
                
            keys = list(query_results[0].keys())
            
            # Smart column detection
            label_key = keys[0]  # First column typically contains labels
            
            # Find the best numeric column for values
            value_key = keys[1]  # Default to second column
            for key in reversed(keys[1:]):  # Check from right to left for best numeric column
                sample_value = query_results[0].get(key)
                if sample_value is not None:
                    try:
                        float(sample_value)
                        value_key = key
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Extract data for chart
            labels = []
            values = []
            
            for row in query_results[:20]:  # Limit to 20 data points for performance
                label = str(row.get(label_key, ''))
                try:
                    value = float(row.get(value_key, 0)) if row.get(value_key) is not None else 0
                except (ValueError, TypeError):
                    value = 0
                    
                labels.append(label)
                values.append(value)
            
            # Chart-specific formatting
            if chart_type in ['pie', 'doughnut']:
                return ChartFormatterTool._format_pie_chart(labels, values, value_key, label_key)
            else:
                return ChartFormatterTool._format_standard_chart(chart_type, labels, values, value_key, label_key)
                
        except Exception as e:
            print(f"Error in ChartFormatterTool: {e}")
            return None
    
    @staticmethod
    def _format_standard_chart(chart_type: str, labels: List[str], values: List[float], 
                             value_key: str, label_key: str) -> Dict[str, Any]:
        """Format data for bar, line, area charts"""
        return {
            "type": chart_type,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": value_key.replace('_', ' ').title(),
                    "data": values,
                    "backgroundColor": ChartFormatterTool._get_colors(len(values), 0.6),
                    "borderColor": ChartFormatterTool._get_colors(len(values), 1.0),
                    "borderWidth": 2,
                    "fill": chart_type == 'area'
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{value_key.replace('_', ' ').title()} by {label_key.replace('_', ' ').title()}"
                    },
                    "legend": {
                        "display": True
                    }
                }
            },
            "title": f"{value_key.replace('_', ' ').title()} by {label_key.replace('_', ' ').title()}"
        }
    
    @staticmethod  
    def _format_pie_chart(labels: List[str], values: List[float], 
                         value_key: str, label_key: str) -> Dict[str, Any]:
        """Format data for pie/doughnut charts"""
        return {
            "type": "pie",
            "data": {
                "labels": labels,
                "datasets": [{
                    "data": values,
                    "backgroundColor": ChartFormatterTool._get_colors(len(values), 0.8),
                    "borderColor": ChartFormatterTool._get_colors(len(values), 1.0),
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{value_key.replace('_', ' ').title()} Distribution"
                    },
                    "legend": {
                        "display": True,
                        "position": "bottom"
                    }
                }
            },
            "title": f"{value_key.replace('_', ' ').title()} Distribution"
        }
    
    @staticmethod
    def _get_colors(count: int, alpha: float) -> List[str]:
        """Generate color palette for charts"""
        base_colors = [
            f"rgba(0, 229, 255, {alpha})",      # Cyan
            f"rgba(255, 99, 132, {alpha})",     # Red
            f"rgba(54, 162, 235, {alpha})",     # Blue
            f"rgba(255, 206, 86, {alpha})",     # Yellow
            f"rgba(75, 192, 192, {alpha})",     # Teal
            f"rgba(153, 102, 255, {alpha})",    # Purple
            f"rgba(255, 159, 64, {alpha})",     # Orange
            f"rgba(199, 199, 199, {alpha})",    # Gray
            f"rgba(83, 102, 255, {alpha})",     # Indigo
            f"rgba(255, 99, 255, {alpha})"      # Magenta
        ]
        
        # Repeat colors if we need more than base set
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
        return colors


class TableFormatterTool:
    """Tool for formatting data into table-ready format"""
    
    @staticmethod
    def format_table_data(query_results: List[Dict[str, Any]], display_type: str) -> Optional[Dict[str, Any]]:
        """
        Format query results into table data
        
        Args:
            query_results: Raw SQL query results
            display_type: LLM-determined display type
            
        Returns:
            Formatted table data or None if not applicable
        """
        if display_type != 'table' or not query_results:
            return None
            
        try:
            # Limit rows for performance (frontend can paginate)
            limited_results = query_results[:100]
            
            # Clean and format data
            formatted_data = []
            for row in limited_results:
                formatted_row = {}
                for key, value in row.items():
                    # Clean column names
                    clean_key = key.replace('_', ' ').title()
                    
                    # Format values
                    if value is None:
                        formatted_value = ''
                    elif isinstance(value, (int, float)):
                        # Format numbers appropriately
                        if key.lower().endswith(('amount', 'price', 'total', 'spent', 'revenue')):
                            formatted_value = f"${value:,.2f}"
                        elif isinstance(value, float) and value.is_integer():
                            formatted_value = int(value)
                        else:
                            formatted_value = value
                    elif hasattr(value, 'isoformat'):  # DateTime objects
                        formatted_value = value.strftime("%Y-%m-%d %H:%M")
                    else:
                        formatted_value = str(value)
                    
                    formatted_row[clean_key] = formatted_value
                
                formatted_data.append(formatted_row)
            
            return {
                "type": "table",
                "data": formatted_data,
                "columns": list(formatted_data[0].keys()) if formatted_data else [],
                "total_rows": len(query_results),
                "displayed_rows": len(formatted_data),
                "title": "Query Results"
            }
            
        except Exception as e:
            print(f"Error in TableFormatterTool: {e}")
            return None


class ListFormatterTool:
    """Tool for formatting data into list format"""
    
    @staticmethod
    def format_list_data(query_results: List[Dict[str, Any]], display_type: str) -> Optional[Dict[str, Any]]:
        """
        Format query results into list data
        
        Args:
            query_results: Raw SQL query results  
            display_type: LLM-determined display type
            
        Returns:
            Formatted list data or None if not applicable
        """
        if display_type != 'list' or not query_results:
            return None
            
        try:
            # Different list formatting strategies based on data structure
            keys = list(query_results[0].keys()) if query_results else []
            
            if len(keys) == 1:
                # Single column - simple list
                items = [str(row[keys[0]]) for row in query_results[:20]]
                return {
                    "type": "simple_list",
                    "items": items,
                    "title": keys[0].replace('_', ' ').title()
                }
            elif len(keys) == 2:
                # Two columns - key-value pairs
                items = []
                for row in query_results[:20]:
                    key_val = f"{row[keys[0]]}: {row[keys[1]]}"
                    items.append(key_val)
                return {
                    "type": "key_value_list",
                    "items": items,
                    "title": f"{keys[0].replace('_', ' ').title()} and {keys[1].replace('_', ' ').title()}"
                }
            else:
                # Multiple columns - structured list
                items = []
                for row in query_results[:20]:
                    # Create a summary line for each row
                    primary_field = str(row[keys[0]])
                    details = []
                    for key in keys[1:3]:  # Show up to 2 additional fields
                        if row[key] is not None:
                            details.append(f"{key.replace('_', ' ')}: {row[key]}")
                    
                    if details:
                        item = f"{primary_field} ({', '.join(details)})"
                    else:
                        item = primary_field
                    
                    items.append(item)
                
                return {
                    "type": "structured_list", 
                    "items": items,
                    "title": keys[0].replace('_', ' ').title()
                }
                
        except Exception as e:
            print(f"Error in ListFormatterTool: {e}")
            return None


class ResponseFormatterTool:
    """Master tool that coordinates all formatting based on display_type"""
    
    @staticmethod
    def format_response_data(query_results: List[Dict[str, Any]], 
                           display_type: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Format query results using appropriate tools based on display_type
        
        Args:
            query_results: Raw SQL query results
            display_type: LLM-determined display type
            
        Returns:
            Tuple of (chart_data, table_data, list_data) - only one will be populated based on display_type
        """
        chart_data = None
        table_data = None  
        list_data = None
        
        try:
            if display_type.startswith('chart_'):
                chart_data = ChartFormatterTool.format_chart_data(query_results, display_type)
            elif display_type == 'table':
                table_data = TableFormatterTool.format_table_data(query_results, display_type)
            elif display_type == 'list':
                list_data = ListFormatterTool.format_list_data(query_results, display_type)
            
            # Always provide fallback data regardless of display_type
            # This ensures frontend has all options available
            if not table_data and query_results:
                table_data = TableFormatterTool.format_table_data(query_results, 'table')
            
        except Exception as e:
            print(f"Error in ResponseFormatterTool: {e}")
            # Provide minimal fallback
            if query_results:
                table_data = {"type": "table", "data": query_results[:50], "error": str(e)}
        
        return chart_data, table_data, list_data