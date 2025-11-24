from pydantic import BaseModel
from typing import Optional, List

# --- Risk Models ---
class RiskCalculationRequest(BaseModel):
    entry_price: float
    high: float
    low: float
    signal_type: str
    account_balance: float
    risk_percent: float = 1.0
    reward_ratio: float = 2.0

# --- Checklist Models ---
class ChecklistUpdate(BaseModel):
    item: str
    change: int
    month: Optional[str] = None

# --- News Models ---
class NewsCreate(BaseModel):
    date: str
    time: Optional[str] = None
    source: Optional[str] = None
    title: str
    content: str
    url: Optional[str] = None
    ai_analysis: Optional[str] = None
    sentiment: Optional[str] = None
    impact_score: Optional[int] = None
    tags: Optional[List[str]] = []

class NewsUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    ai_analysis: Optional[str] = None
    sentiment: Optional[str] = None
    impact_score: Optional[int] = None
    tags: Optional[List[str]] = None
