# Bug Fix: Database Sync Duplicate Files

## 🐛 Problem

ทุกครั้งที่เปิด-ปิด backend จะสร้างไฟล์ซ้ำ:
```
market_data_v0.1.json
market_data_v0.2.json
market_data_v0.3.json
checklist_monthly_v0.1.json
checklist_monthly_v0.2.json
checklist_monthly_v0.3.json
```

Version ไม่เพิ่มขึ้นถูกต้อง → สร้างไฟล์ซ้ำทุกครั้ง

---

## 🔍 Root Cause

### **Bug #1: Missing Import Logic**

ใน `import_table_from_file()` (line 197-221):

**Before:**
```python
def import_table_from_file(filepath: str) -> bool:
    try:
        # ... load JSON ...
        if not records:
            return False
        
        # ❌ NO IMPORT LOGIC HERE!
        
    except Exception as e:
        return False
```

**ปัญหา:**
- Function แค่ load JSON แล้ว return False
- ไม่มีการ import ข้อมูลเข้า database จริง
- `imported_versions` ไม่ถูก update
- Export ครั้งต่อไป → ใช้ version เดิม → ไฟล์ซ้ำ!

---

### **Bug #2: No Cleanup**

ไม่มี logic ลบไฟล์เก่า → ไฟล์สะสมเรื่อยๆ

---

## ✅ Solution

### **Fix #1: Add Import Logic**

```python
def import_table_from_file(filepath: str) -> bool:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        table_name = data['table']
        version = data['version']
        records = data['data']
        
        if not records:
            return False
        
        # ✅ Convert to DataFrame
        df = pd.DataFrame(records)
        
        # ✅ Import to database (upsert strategy)
        if table_name == "market_data":
            for _, row in df.iterrows():
                db.upsert_market_data_row(row.to_dict())
        elif table_name == "journal_entries":
            for _, row in df.iterrows():
                db.upsert_journal_entry(row.to_dict())
        elif table_name == "checklist_monthly":
            for _, row in df.iterrows():
                db.upsert_checklist_entry(row.to_dict())
        elif table_name == "news_analysis":
            for _, row in df.iterrows():
                db.upsert_news_entry(row.to_dict())
        
        print(f"[IMPORT] {table_name} v{version} → {len(df)} rows")
        return True  # ✅ Return True on success
        
    except Exception as e:
        print(f"[ERROR] Failed to import: {e}")
        return False
```

---

### **Fix #2: Add Cleanup Function**

```python
def cleanup_old_versions(table_name: str, keep_count: int = 3):
    """
    Remove old version files, keeping only the latest N versions
    """
    table_dir = SYNC_DIR / table_name
    if not table_dir.exists():
        return
    
    # Get all version files
    version_files = sorted(table_dir.glob(f"{table_name}_v*.json"))
    
    # Keep only latest N
    if len(version_files) > keep_count:
        files_to_delete = version_files[:-keep_count]
        for file in files_to_delete:
            file.unlink()
            print(f"[CLEANUP] Removed old version: {file.name}")
```

**Call in `export_all_tables()`:**
```python
# After export
cleanup_old_versions(table_name, keep_count=3)
```

---

## 📊 How It Works Now

### **Scenario 1: First Export**
```
1. Export market_data → v0.1 ✅
2. Save metadata: {"versions": {"market_data": "0.1"}}
3. No cleanup (only 1 file)
```

### **Scenario 2: Second Export**
```
1. Read metadata: current version = 0.1
2. Increment: 0.1 → 0.2
3. Export market_data → v0.2 ✅
4. Save metadata: {"versions": {"market_data": "0.2"}}
5. Cleanup: Keep v0.2, v0.1 (latest 2)
```

### **Scenario 3: Import from Other OS**
```
1. Find files: market_data_v0.1, v0.2
2. Check imported_versions: last = 0.0
3. Import v0.1 ✅
4. Import v0.2 ✅
5. Update metadata: {"imported_versions": {"market_data": "0.2"}}
```

### **Scenario 4: Export After Import**
```
1. Read metadata: current version = 0.2 (from previous export)
2. Increment: 0.2 → 0.3
3. Export market_data → v0.3 ✅
4. Cleanup: Keep v0.3, v0.2, v0.1 (latest 3)
```

---

## 🎯 Result

### **Before Fix:**
```
data_sync/windows/market_data/
├── market_data_v0.1.json  ← ซ้ำ
├── market_data_v0.2.json  ← ซ้ำ
├── market_data_v0.3.json  ← ซ้ำ
├── market_data_v0.1.json  ← ซ้ำอีก!
├── market_data_v0.2.json  ← ซ้ำอีก!
└── ...                    ← สะสมไม่รู้จบ
```

### **After Fix:**
```
data_sync/windows/market_data/
├── market_data_v0.1.json  ← เก่าสุด
├── market_data_v0.2.json  ← กลาง
└── market_data_v0.3.json  ← ใหม่สุด (keep 3 versions)
```

---

## ✅ Changes Made

### **File: `trading_api/app/services/db_sync.py`**

1. **Line 197-245:** Fixed `import_table_from_file()`
   - Added DataFrame conversion
   - Added upsert logic for all tables
   - Return True on success

2. **Line 196-222:** Added `cleanup_old_versions()`
   - Remove old version files
   - Keep latest 3 versions
   - Prevent disk space waste

3. **Line 180:** Call cleanup after export
   ```python
   cleanup_old_versions(table_name, keep_count=3)
   ```

---

## 🧪 Testing

### **Test 1: Export**
```bash
# Start backend
cd trading_api
uvicorn app.main:app --reload --port 8000

# Stop backend (Ctrl+C)
# Check files
ls data_sync/windows/market_data/
```

**Expected:**
- New version file created
- Old files cleaned up (keep 3)

### **Test 2: Import**
```bash
# Copy data_sync from other OS
# Start backend
# Check logs
```

**Expected:**
```
[IMPORT] market_data v0.2 from macos → 1234 rows
[IMPORT] checklist_monthly v0.1 from macos → 19 rows
```

### **Test 3: Version Increment**
```bash
# Export 5 times
# Check versions
```

**Expected:**
```
v0.1 → v0.2 → v0.3 → v0.4 → v0.5
(Keep only v0.3, v0.4, v0.5)
```

---

## 📝 Configuration

### **Change Keep Count:**

Edit `db_sync.py`:
```python
# Keep more versions
cleanup_old_versions(table_name, keep_count=5)

# Keep fewer versions
cleanup_old_versions(table_name, keep_count=2)
```

### **Disable Cleanup:**

Comment out the cleanup call:
```python
# cleanup_old_versions(table_name, keep_count=3)
```

---

## ⚠️ Important Notes

1. **Cleanup happens on export** - ไม่ลบไฟล์จากเครื่องอื่น
2. **Keep 3 versions** - เพียงพอสำหรับ rollback
3. **Import ทำงานแล้ว** - ข้อมูลจะถูก merge จริง
4. **Version tracking ถูกต้อง** - ไม่ซ้ำอีกแล้ว

---

## ✅ Status

**Fixed:** ✅  
**Date:** 2025-11-25  
**Severity:** Medium (ไม่กระทบการทำงาน แต่สร้างไฟล์ซ้ำ)  
**Impact:** Disk space + Version tracking
