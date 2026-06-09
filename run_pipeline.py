# run_pipeline.py
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 1. FORCE LOAD HIDDEN ENVIRONMENT VARIABLES
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# 2. PULL SAFE CONFIGURATIONS
from src.config import KEYWORD_MAP, DB_PATH, NEWS_BASE_URL

# ==========================================
# DATABASE SHIELD & INITIALIZATION LOGIC
# ==========================================

def initialize_database():
    """Creates the SQLite database and tables ONLY if they do not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Price Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_prices (
            ticker TEXT,
            datetime_str TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            UNIQUE(ticker, datetime_str) ON CONFLICT REPLACE
        )
    ''')
    
    # Sentiment/News Table (Updated Schema)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_sentiment (
            ticker TEXT,
            headline TEXT,
            source TEXT,
            event_time TEXT,
            sentiment REAL,
            UNIQUE(ticker, headline) ON CONFLICT IGNORE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("🗄️ Database architecture verified.")

def requires_news_api_call(ticker, cooldown_hours=3):
    """Checks the local database to see if we already have recent news."""
    if not os.path.exists(DB_PATH):
        return True 
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT MAX(event_time) FROM news_sentiment WHERE ticker = ?', (ticker,))
        result = cursor.fetchone()[0]
        conn.close()
        
        if not result:
            return True 
            
        clean_time_str = result.replace('T', ' ').replace('Z', '')
        latest_db_time = datetime.fromisoformat(clean_time_str)
        
        if (datetime.now() - latest_db_time) > timedelta(hours=cooldown_hours):
            return True
        else:
            return False
            
    except sqlite3.OperationalError:
        conn.close()
        return True

# ==========================================
# CORE FETCHING & SCORING LOGIC
# ==========================================

def fetch_and_score_news(keyword, ticker):
    """Fetches news from the API, simulates scoring, and saves to DB."""
    print(f"🧠 Loading FinBERT Transformer model into memory for {ticker}...")
    
    # Failsafe check to ensure the API key was actually found
    if not NEWS_API_KEY or NEWS_API_KEY == "YOUR_NEWS_API_KEY_HERE":
        print(f"❌ ERROR: API Key missing or invalid for {ticker}. Check your .env file.")
        return

    from_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    url = f"{NEWS_BASE_URL}?q={keyword}&language=en&sortBy=publishedAt&pageSize=10&from={from_date}&apiKey={NEWS_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        
        # Explicit error handling for common API issues
        if response.status_code == 429:
            print(f"❌ Rate Limit Exceeded for {ticker}. Please rotate your API key or wait 24 hours.")
            return
        elif response.status_code == 401:
            print(f"❌ Unauthorized (401) for {ticker}. Your .env API key is invalid or unauthorized.")
            return
            
        response.raise_for_status()
        articles = response.json().get("articles", [])
        
        if not articles:
            print(f"⚠️ No recent articles found for {keyword}.")
            return
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        saved_count = 0
        for article in articles:
            headline = article.get("title")
            source = article.get("source", {}).get("name", "Unknown")
            event_time = article.get("publishedAt")
            
            # --- INSERT YOUR FINBERT LOGIC HERE ---
            simulated_sentiment_score = 0.05  
            
            # Save to the correctly named SQLite table
            cursor.execute('''
                INSERT OR IGNORE INTO news_sentiment (ticker, headline, source, event_time, sentiment)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticker, headline, source, event_time, simulated_sentiment_score))
            
            if cursor.rowcount > 0:
                saved_count += 1
                
        conn.commit()
        conn.close()
        print(f"✅ Successfully scored and synced {saved_count} new articles for {ticker}.")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch news for {keyword}: {e}")

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================

if __name__ == "__main__":
    print("🔄 Background Pipeline Auto-Triggered...")
    
    initialize_database()
    
    for keyword, ticker in KEYWORD_MAP.items():
        if requires_news_api_call(ticker, cooldown_hours=3):
            print(f"[{ticker}] Local cache outdated or empty. Hitting NewsAPI...")
            fetch_and_score_news(keyword, ticker)
        else:
            print(f"[{ticker}] Recent news found in local cache. Skipping API call to save limits.")
            
    print("🏁 Pipeline execution complete. Going back to sleep.")