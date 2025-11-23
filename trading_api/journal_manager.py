from typing import List, Dict, Optional
from pydantic import BaseModel
from db_manager import db

class JournalEntry(BaseModel):
    date: str
    trade1: Optional[float] = 0.0
    trade2: Optional[float] = 0.0
    trade3: Optional[float] = 0.0
    deposit: Optional[float] = 0.0
    withdraw: Optional[float] = 0.0
    note: Optional[str] = ""
    
    # Computed/Stored values
    profit: Optional[float] = 0.0
    total: Optional[float] = 0.0
    capital: Optional[float] = 0.0 # Starting capital for the day
    winrate: Optional[float] = 0.0 # Daily winrate %

class JournalManager:
    def __init__(self):
        pass

    def get_entries(self) -> List[Dict]:
        return db.get_journal_entries()

    def save_entry(self, entry: JournalEntry):
        # 1. Prepare current entry data
        entry_dict = entry.dict()
        
        # Calculate Profit & Winrate for this entry
        trades = [t for t in [entry.trade1, entry.trade2, entry.trade3] if t is not None]
        entry_dict['profit'] = sum(trades)
        
        winning_trades = len([t for t in trades if t > 0])
        total_trades_count = len([t for t in trades if t != 0])
        if total_trades_count > 0:
            entry_dict['winrate'] = round((winning_trades / total_trades_count) * 100, 2)
        else:
            entry_dict['winrate'] = 0.0

        # 2. Get all existing entries to recalculate running totals
        all_entries = self.get_entries()
        
        # Remove existing version of this entry if exists (to avoid duplication in list)
        all_entries = [e for e in all_entries if e['date'] != entry.date]
        
        # Add new/updated entry
        all_entries.append(entry_dict)
        
        # Sort by date
        all_entries.sort(key=lambda x: x['date'])
        
        # 3. Recalculate Running Total
        running_total = 0.0
        
        updated_entries = []
        
        for i, e in enumerate(all_entries):
            profit = e.get('profit', 0.0) or 0.0
            deposit = e.get('deposit', 0.0) or 0.0
            withdraw = e.get('withdraw', 0.0) or 0.0
            capital = e.get('capital', 0.0) or 0.0
            
            if i == 0:
                # First entry: Total = Capital + Profit + Deposit - Withdraw
                # If capital is 0, maybe we should try to infer it? No, just trust user input.
                running_total = capital + profit + deposit - withdraw
            else:
                # Subsequent: Total = Previous Total + Profit + Deposit - Withdraw
                # Note: 'capital' field in subsequent entries might be ignored for total calc 
                # unless it represents an adjustment, but usually capital is just for reference or initial.
                # Let's assume 'deposit' handles adding money.
                running_total = running_total + profit + deposit - withdraw
            
            e['total'] = round(running_total, 2)
            updated_entries.append(e)
            
        # 4. Save all updated entries to DB
        # This is important because changing one early entry affects all subsequent totals
        for e in updated_entries:
            db.save_journal_entry(e)
            
        return entry_dict

    def delete_entry(self, date: str):
        db.delete_journal_entry(date)
        
        # Recalculate totals after deletion
        # We just trigger a save of the first entry? No, need to fetch all and recalc.
        all_entries = self.get_entries() # This will now exclude the deleted one
        
        if not all_entries:
            return

        running_total = 0.0
        for i, e in enumerate(all_entries):
            profit = e.get('profit', 0.0) or 0.0
            deposit = e.get('deposit', 0.0) or 0.0
            withdraw = e.get('withdraw', 0.0) or 0.0
            capital = e.get('capital', 0.0) or 0.0
            
            if i == 0:
                running_total = capital + profit + deposit - withdraw
            else:
                running_total = running_total + profit + deposit - withdraw
            
            e['total'] = round(running_total, 2)
            db.save_journal_entry(e)
