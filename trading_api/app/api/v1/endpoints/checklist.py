from fastapi import APIRouter, HTTPException
from typing import Optional
from app.models.schemas import ChecklistUpdate
from app.services.checklist import ChecklistManager

router = APIRouter()
checklist_manager = ChecklistManager()

@router.get("/checklist")
def get_checklist(month: Optional[str] = None):
    try:
        return checklist_manager.get_data(month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/checklist/update")
def update_checklist(update: ChecklistUpdate):
    try:
        return checklist_manager.update_count(update.item, update.change, update.month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
