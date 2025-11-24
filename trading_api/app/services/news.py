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
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS news_analysis (
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
                    )
                """)
                
                # Create index for faster search
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_news_date ON news_analysis(date DESC);
                    CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_analysis(sentiment);
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
        
        Args:
            news_data: {
                'date': '2025-11-23',
                'time': '10:00',
                'source': 'Reuters',
                'title': 'News title',
                'content': 'Full news content',
                'url': 'https://...',
                'ai_analysis': 'AI analysis result (optional)',
                'sentiment': 'POSITIVE/NEGATIVE/NEUTRAL (optional)',
                'impact_score': 1-10 (optional),
                'tags': ['gold', 'fed', 'inflation']
            }
        
        Returns:
            Created news entry with ID
        """
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO news_analysis 
                    (date, time, source, title, content, url, ai_analysis, sentiment, impact_score, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    news_data.get('date'),
                    news_data.get('time'),
                    news_data.get('source'),
                    news_data.get('title'),
                    news_data.get('content'),
                    news_data.get('url'),
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
                    SELECT id, date, time, source, title, content, url, 
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
                    'ai_analysis': row[7],
                    'sentiment': row[8],
                    'impact_score': row[9],
                    'tags': row[10] or [],
                    'created_at': str(row[11]),
                    'updated_at': str(row[12])
                }
        finally:
            db.return_connection(conn)
    
    def get_all_news(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Get all news entries with pagination"""
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, date, time, source, title, content, url,
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
                    'ai_analysis': row[7],
                    'sentiment': row[8],
                    'impact_score': row[9],
                    'tags': row[10] or [],
                    'created_at': str(row[11]),
                    'updated_at': str(row[12])
                } for row in rows]
        finally:
            db.return_connection(conn)
    
    def update_news(self, news_id: int, updates: dict) -> dict:
        """
        Update a news entry.
        
        Args:
            news_id: ID of news to update
            updates: Dictionary of fields to update
        """
        conn = db.get_connection()
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            
            allowed_fields = ['date', 'time', 'source', 'title', 'content', 'url',
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
                   tags: Optional[List[str]] = None,
                   limit: int = 100) -> List[dict]:
        """
        Search news with various filters.
        
        Args:
            keyword: Search in title and content
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            sentiment: POSITIVE/NEGATIVE/NEUTRAL
            source: News source
            tags: List of tags to filter
            limit: Maximum results
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
            
            if tags:
                conditions.append("tags && %s")
                values.append(tags)
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            values.append(limit)
            
            with conn.cursor() as cur:
                query = f"""
                    SELECT id, date, time, source, title, content, url,
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
                    'ai_analysis': row[7],
                    'sentiment': row[8],
                    'impact_score': row[9],
                    'tags': row[10] or [],
                    'created_at': str(row[11]),
                    'updated_at': str(row[12])
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

# Global instance
news_manager = NewsManager()
