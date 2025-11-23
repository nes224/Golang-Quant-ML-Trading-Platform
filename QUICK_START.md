# NesHedgeFund - Quick Start Scripts

## สำหรับ MacOS (Yahoo Finance)

### 1. สร้างไฟล์ `.env`
```bash
# ใน trading_api/.env
DATA_SOURCE=YAHOO
```

### 2. Start Server
```bash
cd trading_api
export DATA_SOURCE=YAHOO
uvicorn main:app --reload --port 8000
```

### 3. Start Frontend
```bash
cd trading_web
npm run dev
```

---

## สำหรับ Windows (MT5)

### 1. สร้างไฟล์ `.env`
```powershell
# ใน trading_api/.env
DATA_SOURCE=MT5
MT5_LOGIN=206646872
MT5_PASSWORD=245026772451Pn@
MT5_SERVER=Exness-MT5Trial7
```

### 2. Start Server (PowerShell)
```powershell
cd trading_api
$env:DATA_SOURCE="MT5"
uvicorn main:app --reload --port 8000
```

### 3. Start Frontend
```powershell
cd trading_web
npm run dev
```

---

## 🚀 One-Click Start Scripts

### MacOS: `start_macos.sh`
```bash
#!/bin/bash
export DATA_SOURCE=YAHOO
cd trading_api && uvicorn main:app --reload --port 8000 &
cd trading_web && npm run dev
```

### Windows: `start_windows.bat`
```batch
@echo off
set DATA_SOURCE=MT5
start cmd /k "cd trading_api && uvicorn main:app --reload --port 8000"
start cmd /k "cd trading_web && npm run dev"
```

---

## 📊 ตรวจสอบ Data Source ปัจจุบัน

เปิดเว็บแล้วดูที่ Console หรือเรียก API:
```
GET http://localhost:8000/
```

Response จะบอกว่าใช้ Data Source อะไร

---

## 💡 Tips

1. **Auto-detect Platform**:
   - ระบบจะพยายาม detect MT5 อัตโนมัติ
   - ถ้าไม่เจอจะ fallback เป็น Yahoo

2. **Database Sync**:
   - ข้อมูลจาก Yahoo และ MT5 จะเก็บในตาราง cache เดียวกัน
   - สลับ source ได้เลยไม่ต้องกังวล

3. **Performance**:
   - Yahoo: Delayed 15-20 min, เหมาะสำหรับ analysis
   - MT5: Real-time, เหมาะสำหรับ active trading
