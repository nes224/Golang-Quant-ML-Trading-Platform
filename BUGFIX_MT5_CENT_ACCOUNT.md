# MT5 Cent Account Support

## 🐛 Problem

เมื่อเปลี่ยนไปใช้บัญชี **Cent Account** ใน MT5:

```
Error: Failed to select XAUUSD, error code = (-1, 'Terminal: Call failed')
```

## 🔍 Root Cause

**Cent Account** ใช้ symbol ที่แตกต่างจากบัญชีปกติ:

### **บัญชีปกติ:**
- Symbol: `XAUUSD`

### **บัญชี Cent:**
- Symbol: `XAUUSDc` ← มี **"c"** ต่อท้าย!
- หรือ: `XAUUSDcent`

ระบบเดิมไม่มี variation สำหรับ Cent account → ทำให้ select symbol ไม่ได้

---

## ✅ Solution

เพิ่ม **XAUUSDc** และ **XAUUSDcent** ใน symbol variations

### **Files Modified:**

#### **1. `trading_api/app/services/data_provider.py`**

**Before:**
```python
variations = ["GOLD", "XAUUSDm", "XAUUSD.", "XAUUSD+", "XAUUSD_i"]
```

**After:**
```python
variations = ["XAUUSDc", "GOLD", "XAUUSDm", "XAUUSD.", "XAUUSD+", "XAUUSD_i", "XAUUSDcent"]
```

#### **2. `trading_api/app/services/market_stream.py`**

**Before:**
```python
variations = ["GOLD", "XAUUSDm", "XAUUSD.", "XAUUSD+", "XAUUSD_i"]
```

**After:**
```python
variations = ["XAUUSDc", "GOLD", "XAUUSDm", "XAUUSD.", "XAUUSD+", "XAUUSD_i", "XAUUSDcent"]
```

---

## 🎯 How It Works

### **Symbol Detection Flow:**

```
1. Try to select "XAUUSD"
   ↓
2. Failed? Try variations in order:
   ✅ XAUUSDc      ← Cent Account (NEW!)
   ✅ GOLD
   ✅ XAUUSDm      ← Micro Account
   ✅ XAUUSD.
   ✅ XAUUSD+
   ✅ XAUUSD_i
   ✅ XAUUSDcent   ← Cent Account (NEW!)
   ↓
3. Found? Use that symbol
   ↓
4. Not found? Return error
```

### **Example Output:**

```
✅ Found alternative symbol: XAUUSDc
```

---

## 🧪 Testing

### **Test 1: Cent Account**
```bash
# Start backend with MT5
cd trading_api
uvicorn app.main:app --reload --port 8000
```

**Expected:**
```
✅ Found alternative symbol: XAUUSDc
[INFO] Market data fetched successfully
```

### **Test 2: Regular Account**
```bash
# Switch back to regular account
# Restart backend
```

**Expected:**
```
[INFO] Symbol XAUUSD selected
[INFO] Market data fetched successfully
```

---

## 📊 Supported Account Types

| Account Type | Symbol | Status |
|--------------|--------|--------|
| Regular | XAUUSD | ✅ Supported |
| Cent | XAUUSDc | ✅ Supported (NEW!) |
| Cent | XAUUSDcent | ✅ Supported (NEW!) |
| Micro | XAUUSDm | ✅ Supported |
| Other | GOLD | ✅ Supported |
| Other | XAUUSD. | ✅ Supported |
| Other | XAUUSD+ | ✅ Supported |
| Other | XAUUSD_i | ✅ Supported |

---

## 💡 Notes

### **Priority Order:**
1. **XAUUSDc** - ลองก่อน (เพราะ Cent account ใช้บ่อย)
2. **GOLD** - บาง broker ใช้
3. **XAUUSDm** - Micro account
4. **อื่นๆ** - Variations อื่น

### **Why "c" suffix?**
- **c** = Cent
- Cent account = 1 lot = $1,000 (แทนที่จะเป็น $100,000)
- เหมาะสำหรับ demo หรือ small account

### **Broker Variations:**
แต่ละ broker อาจใช้ชื่อต่างกัน:
- **XM**: `XAUUSDc`
- **Exness**: `XAUUSDcent`
- **IC Markets**: `XAUUSD`
- **Pepperstone**: `GOLD`

---

## ✅ Status

**Fixed:** ✅  
**Date:** 2025-11-26  
**Impact:** Cent Account users can now use the system  
**Backward Compatible:** Yes (ไม่กระทบบัญชีปกติ)
