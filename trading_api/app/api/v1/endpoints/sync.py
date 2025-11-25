"""
Database Sync API Endpoints
"""

from fastapi import APIRouter, HTTPException
from app.services.db_sync import (
    export_all_tables,
    import_from_other_os,
    get_sync_status,
    CURRENT_OS
)

router = APIRouter()


@router.post("/export")
def export_database():
    """
    Manually trigger database export
    
    Returns:
        Dictionary with exported file paths
    """
    try:
        exported_files = export_all_tables()
        return {
            "status": "success",
            "os": CURRENT_OS,
            "exported_files": exported_files,
            "message": f"Database exported successfully ({len(exported_files)} tables)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
def import_database():
    """
    Manually trigger database import from other OS
    
    Returns:
        Dictionary with import statistics
    """
    try:
        stats = import_from_other_os()
        return {
            "status": "success",
            "os": CURRENT_OS,
            "import_stats": stats,
            "message": f"Data imported successfully from other OS"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def sync_status():
    """
    Get current sync status
    
    Returns:
        Sync metadata and available imports
    """
    try:
        status = get_sync_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/force-export/{table_name}")
def force_export_table(table_name: str):
    """
    Force export a specific table
    
    Args:
        table_name: Name of the table to export
    """
    try:
        from app.services.db_sync import TABLES_TO_SYNC, get_next_version, export_table_to_file
        from app.core.database import db
        
        if table_name not in TABLES_TO_SYNC:
            raise HTTPException(status_code=400, detail=f"Invalid table name. Must be one of: {TABLES_TO_SYNC}")
        
        # Get data
        query = f"SELECT * FROM {table_name}"
        df = db.execute_query(query)
        
        if df is None or df.empty:
            return {
                "status": "skipped",
                "message": f"No data in {table_name}"
            }
        
        # Export
        version = get_next_version(table_name)
        filepath = export_table_to_file(table_name, df, version)
        
        return {
            "status": "success",
            "table": table_name,
            "version": version,
            "filepath": filepath,
            "row_count": len(df)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
