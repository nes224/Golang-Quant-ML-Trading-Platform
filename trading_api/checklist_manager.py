from typing import Dict, Optional
from db_manager import db

class ChecklistManager:
    def __init__(self):
        pass

    def get_data(self, month: Optional[str] = None) -> Dict:
        if not month:
            from datetime import datetime
            month = datetime.now().strftime("%Y-%m")
            
        return db.get_checklist(month)

    def update_count(self, item: str, change: int, month: Optional[str] = None):
        if not month:
            from datetime import datetime
            month = datetime.now().strftime("%Y-%m")
            
        return db.update_checklist_item(month, item, change)
