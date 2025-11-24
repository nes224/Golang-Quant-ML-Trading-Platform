from fastapi import APIRouter
from app.services.analysis.reference import get_dxy_analysis, get_all_reference_indicators

router = APIRouter()

@router.get("/dxy")
def get_dxy(timeframe: str = "1d"):
    """
    Get DXY (US Dollar Index) analysis
    
    Args:
        timeframe: Timeframe to analyze (1d, 4h, 1h)
    
    Returns:
        DXY analysis with trend, price, and interpretation
    """
    return get_dxy_analysis(timeframe)

@router.get("/reference_indicators")
def get_reference_indicators_endpoint():
    """
    Get all reference indicators (DXY, etc.) for multiple timeframes
    
    Returns:
        Dictionary with all reference indicator data
    """
    return get_all_reference_indicators()
