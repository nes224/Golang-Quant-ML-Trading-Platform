import os
from datetime import datetime
from typing import Optional, List
from app.core.database import db

class NewsManager:
    """
    Manages news articles and their AI analysis.
    """
    
    def __init__(self):
        self._ensure_table()
    
    def _ensure_table(self):
        """Create news table if not exists"""
        if db.connection_pool is None:
            print("[WARNING] Database not available. News features will be disabled.")
            return
            
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                # Create table if not exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS news_analysis (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        time VARCHAR(10),
                        source VARCHAR(255),
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        url TEXT,
                        type VARCHAR(50),
                        ai_analysis TEXT,
                        sentiment VARCHAR(50),
                        impact_score INTEGER,
                        tags TEXT[],
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check if 'type' column exists (for migration)
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='news_analysis' AND column_name='type'
                """)
                if not cur.fetchone():
                    print("Migrating news_analysis table: Adding 'type' column...")
                    cur.execute("ALTER TABLE news_analysis ADD COLUMN type VARCHAR(50)")
                
                # Create index for faster search
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_news_date ON news_analysis(date DESC);
                    CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_analysis(sentiment);
                    CREATE INDEX IF NOT EXISTS idx_news_type ON news_analysis(type);
                """)
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to create news table: {e}")
        finally:
            db.return_connection(conn)
    
    def create_news(self, news_data: dict) -> dict:
        """
        Create a new news entry.
        """
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO news_analysis 
                    (date, time, source, title, content, url, type, ai_analysis, sentiment, impact_score, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    news_data.get('date'),
                    news_data.get('time'),
                    news_data.get('source'),
                    news_data.get('title'),
                    news_data.get('content'),
                    news_data.get('url'),
                    news_data.get('type'),
                    news_data.get('ai_analysis'),
                    news_data.get('sentiment'),
                    news_data.get('impact_score'),
                    news_data.get('tags', [])
                ))
                
                result = cur.fetchone()
                conn.commit()
                
                return {
                    'id': result[0],
                    'created_at': result[1],
                    **news_data
                }
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create news: {e}")
        finally:
            db.return_connection(conn)
    
    def get_news(self, news_id: int) -> Optional[dict]:
        """Get a single news entry by ID"""
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, date, time, source, title, content, url, type,
                           ai_analysis, sentiment, impact_score, tags,
                           created_at, updated_at
                    FROM news_analysis
                    WHERE id = %s
                """, (news_id,))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                return {
                    'id': row[0],
                    'date': str(row[1]),
                    'time': row[2],
                    'source': row[3],
                    'title': row[4],
                    'content': row[5],
                    'url': row[6],
                    'type': row[7],
                    'ai_analysis': row[8],
                    'sentiment': row[9],
                    'impact_score': row[10],
                    'tags': row[11] or [],
                    'created_at': str(row[12]),
                    'updated_at': str(row[13])
                }
        finally:
            db.return_connection(conn)
    
    def get_all_news(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Get all news entries with pagination"""
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, date, time, source, title, content, url, type,
                           ai_analysis, sentiment, impact_score, tags,
                           created_at, updated_at
                    FROM news_analysis
                    ORDER BY date DESC, time DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                
                rows = cur.fetchall()
                return [{
                    'id': row[0],
                    'date': str(row[1]),
                    'time': row[2],
                    'source': row[3],
                    'title': row[4],
                    'content': row[5],
                    'url': row[6],
                    'type': row[7],
                    'ai_analysis': row[8],
                    'sentiment': row[9],
                    'impact_score': row[10],
                    'tags': row[11] or [],
                    'created_at': str(row[12]),
                    'updated_at': str(row[13])
                } for row in rows]
        finally:
            db.return_connection(conn)
    
    def update_news(self, news_id: int, updates: dict) -> dict:
        """
        Update a news entry.
        """
        conn = db.get_connection()
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            
            allowed_fields = ['date', 'time', 'source', 'title', 'content', 'url', 'type',
                            'ai_analysis', 'sentiment', 'impact_score', 'tags']
            
            for field in allowed_fields:
                if field in updates:
                    set_clauses.append(f"{field} = %s")
                    values.append(updates[field])
            
            if not set_clauses:
                raise ValueError("No valid fields to update")
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(news_id)
            
            with conn.cursor() as cur:
                query = f"""
                    UPDATE news_analysis
                    SET {', '.join(set_clauses)}
                    WHERE id = %s
                    RETURNING id, updated_at
                """
                cur.execute(query, values)
                
                result = cur.fetchone()
                conn.commit()
                
                if not result:
                    raise Exception(f"News ID {news_id} not found")
                
                return self.get_news(news_id)
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to update news: {e}")
        finally:
            db.return_connection(conn)
    
    def search_news(self, 
                   keyword: Optional[str] = None,
                   date_from: Optional[str] = None,
                   date_to: Optional[str] = None,
                   sentiment: Optional[str] = None,
                   source: Optional[str] = None,
                   news_type: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   limit: int = 100) -> List[dict]:
        """
        Search news with various filters.
        """
        conn = db.get_connection()
        try:
            conditions = []
            values = []
            
            if keyword:
                conditions.append("(title ILIKE %s OR content ILIKE %s)")
                values.extend([f"%{keyword}%", f"%{keyword}%"])
            
            if date_from:
                conditions.append("date >= %s")
                values.append(date_from)
            
            if date_to:
                conditions.append("date <= %s")
                values.append(date_to)
            
            if sentiment:
                conditions.append("sentiment = %s")
                values.append(sentiment)
            
            if source:
                conditions.append("source ILIKE %s")
                values.append(f"%{source}%")
                
            if news_type:
                conditions.append("type = %s")
                values.append(news_type)
            
            if tags:
                conditions.append("tags && %s")
                values.append(tags)
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            values.append(limit)
            
            with conn.cursor() as cur:
                query = f"""
                    SELECT id, date, time, source, title, content, url, type,
                           ai_analysis, sentiment, impact_score, tags,
                           created_at, updated_at
                    FROM news_analysis
                    WHERE {where_clause}
                    ORDER BY date DESC, time DESC
                    LIMIT %s
                """
                cur.execute(query, values)
                
                rows = cur.fetchall()
                return [{
                    'id': row[0],
                    'date': str(row[1]),
                    'time': row[2],
                    'source': row[3],
                    'title': row[4],
                    'content': row[5],
                    'url': row[6],
                    'type': row[7],
                    'ai_analysis': row[8],
                    'sentiment': row[9],
                    'impact_score': row[10],
                    'tags': row[11] or [],
                    'created_at': str(row[12]),
                    'updated_at': str(row[13])
                } for row in rows]
        finally:
            db.return_connection(conn)
    
    def delete_news(self, news_id: int) -> bool:
        """Delete a news entry"""
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM news_analysis WHERE id = %s RETURNING id", (news_id,))
                result = cur.fetchone()
                conn.commit()
                return result is not None
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to delete news: {e}")
        finally:
            db.return_connection(conn)
    def calculate_market_sentiment(self, days: int = 3) -> dict:
        """
        Calculate market sentiment specifically for GOLD (XAU/USD).
        
        Logic:
        1. USD/Economy/Fed News (Inverse Correlation):
           - Positive News -> Bearish for Gold (-1)
           - Negative News -> Bullish for Gold (+1)
           
        2. Gold/Mining News (Direct Correlation):
           - Positive News -> Bullish for Gold (+1)
           - Negative News -> Bearish for Gold (-1)
           
        3. Geopolitics/Crisis (Safe Haven):
           - Negative News (Bad event) -> Bullish for Gold (+1)
           - Positive News (Resolution) -> Bearish for Gold (-1)
        
        Returns:
            dict: {
                "score": float (-10 to 10),
                "label": str (e.g. "Strong Bullish"),
                "total_news": int,
                "breakdown": dict
            }
        """
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                # Fetch news from last N days
                cur.execute("""
                    SELECT sentiment, impact_score, title, content, tags
                    FROM news_analysis
                    WHERE date >= CURRENT_DATE - INTERVAL '%s days'
                    AND sentiment IS NOT NULL
                    AND impact_score IS NOT NULL
                """, (days,))
                
                rows = cur.fetchall()
                
                if not rows:
                    return {
                        "score": 0,
                        "label": "Neutral",
                        "total_news": 0,
                        "breakdown": {"bullish": 0, "bearish": 0, "neutral": 0}
                    }
                
                total_score = 0
                total_impact = 0
                breakdown = {"bullish": 0, "bearish": 0, "neutral": 0}
                
                # Keywords for classification
                usd_keywords = ['usd', 'dollar', 'fed', 'federal reserve', 'rate', 'yield', 'economy', 'jobs', 'cpi', 'inflation', 'gdp']
                gold_keywords = ['gold', 'xau', 'bullion', 'metal', 'mining']
                risk_keywords = ['war', 'conflict', 'geopolitics', 'tension', 'crisis', 'attack', 'trade', 'tariff', 'sanction', 'china', 'us-china']
                
                for row in rows:
                    sentiment = row[0].upper()
                    impact = row[1] or 1
                    text = (row[2] + " " + row[3]).lower() # Title + Content
                    tags = [t.lower() for t in (row[4] or [])]
                    
                    # Determine correlation type
                    is_usd_news = any(k in text for k in usd_keywords) or any(k in tags for k in usd_keywords)
                    is_gold_news = any(k in text for k in gold_keywords) or any(k in tags for k in gold_keywords)
                    is_risk_news = any(k in text for k in risk_keywords) or any(k in tags for k in risk_keywords)
                    
                    # Calculate Gold Score
                    gold_score = 0
                    
                    if sentiment == "POSITIVE":
                        if is_gold_news:
                            gold_score = 1 # Good for Gold
                        elif is_usd_news:
                            gold_score = -1 # Good for USD = Bad for Gold
                        elif is_risk_news:
                            gold_score = -1 # Tension easing = Bad for Safe Haven
                        else:
                            gold_score = 1 # Default general positive sentiment (risk-on can be mixed, but let's assume slight bullish or neutral)
                            
                    elif sentiment == "NEGATIVE":
                        if is_gold_news:
                            gold_score = -1 # Bad for Gold
                        elif is_usd_news:
                            gold_score = 1 # Bad for USD = Good for Gold
                        elif is_risk_news:
                            gold_score = 1 # Crisis/War = Good for Gold (Safe Haven)
                        else:
                            gold_score = -1 # General negative sentiment
                            
                    else: # NEUTRAL
                        gold_score = 0
                    
                    # Update breakdown
                    if gold_score > 0:
                        breakdown["bullish"] += 1
                    elif gold_score < 0:
                        breakdown["bearish"] += 1
                    else:
                        breakdown["neutral"] += 1
                    
                    # Weighted score
                    total_score += gold_score * impact
                    total_impact += impact
                
                # Calculate final score (-1 to 1)
                raw_score = total_score / total_impact if total_impact > 0 else 0
                
                # Scale to -10 to 10
                scaled_score = raw_score * 10
                
                # Determine label
                if scaled_score >= 5:
                    label = "Strong Bullish"
                elif scaled_score >= 2:
                    label = "Bullish"
                elif scaled_score <= -5:
                    label = "Strong Bearish"
                elif scaled_score <= -2:
                    label = "Bearish"
                else:
                    label = "Neutral"
                    
                return {
                    "score": round(scaled_score, 2),
                    "label": label,
                    "total_news": len(rows),
                    "breakdown": breakdown
                }
                
        except Exception as e:
            print(f"Error calculating sentiment: {e}")
            return {
                "score": 0,
                "label": "Error",
                "error": str(e)
            }
        finally:
            db.return_connection(conn)
# Global instance
news_manager = NewsManager()
