# News Analysis API Documentation

## 📰 Overview
ระบบจัดการข่าวและการวิเคราะห์ด้วย AI สำหรับการเทรด

---

## 🔌 API Endpoints

### Base URL
```
http://localhost:8000
```

---

## 📝 CRUD Operations

### 1. **CREATE** - สร้างข่าวใหม่

**Endpoint:** `POST /news`

**Request Body:**
```json
{
  "date": "2025-11-23",
  "time": "10:00",
  "source": "Reuters",
  "title": "Fed ประกาศขึ้นดอกเบี้ย 0.25%",
  "content": "เนื้อหาข่าวฉบับเต็ม...",
  "url": "https://reuters.com/...",
  "ai_analysis": "ผลการวิเคราะห์จาก Claude AI",
  "sentiment": "NEGATIVE",
  "impact_score": 8,
  "tags": ["fed", "interest-rate", "gold"]
}
```

**Response:**
```json
{
  "id": 1,
  "date": "2025-11-23",
  "created_at": "2025-11-23T10:00:00",
  ...
}
```

---

### 2. **READ** - อ่านข่าว

#### 2.1 อ่านข่าวทั้งหมด
**Endpoint:** `GET /news?limit=100&offset=0`

**Response:**
```json
[
  {
    "id": 1,
    "date": "2025-11-23",
    "time": "10:00",
    "source": "Reuters",
    "title": "...",
    "content": "...",
    "ai_analysis": "...",
    "sentiment": "NEGATIVE",
    "impact_score": 8,
    "tags": ["fed", "interest-rate"],
    "created_at": "...",
    "updated_at": "..."
  }
]
```

#### 2.2 อ่านข่าวเฉพาะ ID
**Endpoint:** `GET /news/{news_id}`

**Example:** `GET /news/1`

---

### 3. **UPDATE** - แก้ไขข่าว

**Endpoint:** `PUT /news/{news_id}`

**Request Body:** (ส่งเฉพาะฟิลด์ที่ต้องการแก้)
```json
{
  "ai_analysis": "ผลการวิเคราะห์ใหม่จาก Claude",
  "sentiment": "POSITIVE",
  "impact_score": 9
}
```

---

### 4. **DELETE** - ลบข่าว

**Endpoint:** `DELETE /news/{news_id}`

**Example:** `DELETE /news/1`

**Response:**
```json
{
  "message": "News deleted successfully"
}
```

---

### 5. **SEARCH** - ค้นหาข่าว

**Endpoint:** `GET /news/search`

**Query Parameters:**
- `keyword` - ค้นหาใน title และ content
- `date_from` - วันที่เริ่มต้น (YYYY-MM-DD)
- `date_to` - วันที่สิ้นสุด (YYYY-MM-DD)
- `sentiment` - POSITIVE / NEGATIVE / NEUTRAL
- `source` - แหล่งข่าว
- `tags` - tags คั่นด้วย comma (เช่น "fed,gold,inflation")
- `limit` - จำนวนผลลัพธ์สูงสุด

**Examples:**

```bash
# ค้นหาคำว่า "gold"
GET /news/search?keyword=gold

# ค้นหาข่าวเชิงลบในช่วงวันที่
GET /news/search?sentiment=NEGATIVE&date_from=2025-11-01&date_to=2025-11-30

# ค้นหาตาม tags
GET /news/search?tags=fed,interest-rate

# ค้นหาจากแหล่งข่าว
GET /news/search?source=Reuters
```

---

## 📊 Database Schema

```sql
CREATE TABLE news_analysis (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time VARCHAR(10),
    source VARCHAR(255),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT,
    ai_analysis TEXT,
    sentiment VARCHAR(50),
    impact_score INTEGER,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🤖 Integration with Claude AI

### Workflow:
```
1. รับข้อมูลข่าว (Manual / Google Sheets)
   ↓
2. POST /news (บันทึกข่าวลง DB)
   ↓
3. ส่งข่าวให้ Claude AI วิเคราะห์
   ↓
4. PUT /news/{id} (อัปเดตผลการวิเคราะห์)
   ↓
5. GET /news/search (ดึงข่าวที่วิเคราะห์แล้ว)
```

---

## 💡 Usage Examples

### Python Example:
```python
import requests

# Create news
news_data = {
    "date": "2025-11-23",
    "title": "Fed ขึ้นดอกเบี้ย",
    "content": "เนื้อหาข่าว...",
    "tags": ["fed", "gold"]
}
response = requests.post("http://localhost:8000/news", json=news_data)
news_id = response.json()["id"]

# Update with AI analysis
ai_result = "วิเคราะห์โดย Claude: ข่าวนี้มีผลกระทบเชิงลบต่อทองคำ..."
requests.put(f"http://localhost:8000/news/{news_id}", json={
    "ai_analysis": ai_result,
    "sentiment": "NEGATIVE",
    "impact_score": 8
})

# Search
results = requests.get("http://localhost:8000/news/search?sentiment=NEGATIVE")
print(results.json())
```

### JavaScript Example:
```javascript
// Create news
const newsData = {
  date: "2025-11-23",
  title: "Fed ขึ้นดอกเบี้ย",
  content: "เนื้อหาข่าว...",
  tags: ["fed", "gold"]
};

const response = await fetch("http://localhost:8000/news", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(newsData)
});

const news = await response.json();
console.log("Created news ID:", news.id);
```

---

## 🎯 Next Steps

1. **Frontend UI** - สร้างหน้าจัดการข่าว
2. **Claude AI Integration** - เชื่อมต่อกับ Claude API
3. **Google Sheets Sync** - Import/Export ข้อมูล
4. **Notification** - แจ้งเตือนข่าวสำคัญ

---

## 📖 API Documentation (Swagger)

เปิดเว็บเบราว์เซอร์ไปที่:
```
http://localhost:8000/docs
```

จะเห็น Interactive API Documentation ที่สามารถทดสอบ API ได้เลย!
