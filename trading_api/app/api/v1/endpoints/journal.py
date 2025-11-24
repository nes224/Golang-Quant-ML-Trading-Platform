from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.journal import JournalManager, JournalEntry

router = APIRouter()
journal_manager = JournalManager()

@router.get("/journal")
def get_journal_entries():
    try:
        return journal_manager.get_entries()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/journal")
def save_journal_entry(entry: JournalEntry):
    try:
        saved_entry = journal_manager.save_entry(entry)
        return saved_entry
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/journal/{date}")
def delete_journal_entry(date: str):
    try:
        journal_manager.delete_entry(date)
        return {"message": "Entry deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
