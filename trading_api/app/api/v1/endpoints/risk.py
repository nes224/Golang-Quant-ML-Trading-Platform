from fastapi import APIRouter, HTTPException
from app.models.schemas import RiskCalculationRequest
from app.services.risk import calculate_trade_setup

router = APIRouter()

@router.post("/calculate-risk")
def calculate_risk(request: RiskCalculationRequest):
    """
    Calculate position size and risk parameters based on user's strategy.
    """
    try:
        result = calculate_trade_setup(
            request.entry_price,
            request.high,
            request.low,
            request.signal_type,
            request.account_balance,
            request.risk_percent,
            request.reward_ratio
        )
        if not result:
            raise HTTPException(status_code=400, detail="Invalid calculation parameters")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
