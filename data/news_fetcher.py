# data/news_fetcher.py
import os
import re
import sqlite3
import requests
import spacy
import feedparser
import time
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Pull configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_ALIASES, DB_PATH, NEWS_BASE_URL, RSS_FEEDS, USER_AGENTS

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")


print("🧠 Initializing spaCy NLP Engine for Contextual News Filtering...")
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("⏳ Downloading spaCy 'en_core_web_sm' model...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
print("✅ spaCy NLP Engine ready.")


def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=5000)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            headline TEXT,
            description TEXT,
            url TEXT UNIQUE,
            published_at TEXT,
            source TEXT,
            sentiment_score REAL
        )
    ''')
    conn.commit()
    conn.close()


def strict_classify_headline(headline):
    if not headline: return None
    headline_lower = headline.lower()
    doc = None
    
    for ticker, patterns in TICKER_ALIASES.items():
        for pattern in patterns:
            match = re.search(pattern, headline_lower)
            if match:
                matched_text = match.group(0)
                if matched_text != "reliance":
                    return ticker
                    
                if doc is None: doc = nlp(headline)
                    
                for token in doc:
                    if token.text.lower() == "reliance":
                        if token.pos_ == "PROPN" or token.ent_type_ in ["ORG", "PERSON", "PRODUCT", "GPE"]:
                            return ticker
                        if token.text == "Reliance":
                            prev_token = doc[token.i - 1].text.lower() if token.i > 0 else ""
                            blacklist = ["us", "heavy", "over", "on", "reduce", "increased", "their", "more"]
                            if prev_token not in blacklist:
                                return ticker
    return None 


def normalize_and_store(assigned_ticker, headline, description, url_link, published_at, source):
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM raw_news WHERE url = ? OR headline = ?', (url_link, headline))
    
    if cursor.fetchone():
        conn.close()
        return False 
        
    try:
        cursor.execute('''
            INSERT INTO raw_news (ticker, headline, description, url, published_at, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (assigned_ticker, headline, description, url_link, published_at, source))
        conn.commit() 
        conn.close()
        return True 
    except sqlite3.IntegrityError:
        conn.close()
        return False


def fetch_rss_news():
    print("🕸️ Scraping live RSS web feeds (90-Day Lookback Active)...")
    inserted_count = 0
    
    # --- UPDATED: Changed from days=2 to days=90 ---
    # This ensures we extract every piece of historical data the RSS feed has left over.
    cutoff_time = datetime.now() - timedelta(days=90)
    
    for feed_name, feed_url in RSS_FEEDS.items():
        try:
            feedparser.USER_AGENT = random.choice(USER_AGENTS)
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                standardized_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    from time import mktime
                    entry_dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    # Code will now allow articles up to 90 days old
                    if entry_dt < cutoff_time:
                        continue 
                    
                    standardized_date = entry_dt.strftime("%Y-%m-%d %H:%M:%S")
                
                headline = entry.get("title", "")
                description = entry.get("summary", "")
                url_link = entry.get("link", "")
                source = feed_name  # Natively uses our dictionary names now!
                
                assigned_ticker = strict_classify_headline(headline)
                if assigned_ticker:
                    if normalize_and_store(assigned_ticker, headline, description, url_link, standardized_date, source):
                        inserted_count += 1
                        
            sleep_time = random.uniform(2.0, 5.0)
            print(f"   [Sleeping for {sleep_time:.1f}s to avoid rate limits...]")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"⚠️ RSS Scrape Error for {feed_name}: {e}")
            
    return inserted_count


def fetch_and_store_news(query_string):
    rss_saved = fetch_rss_news()
    api_saved = 0
    
    if NEWS_API_KEY and NEWS_API_KEY != "YOUR_NEWS_API_KEY_HERE":
        end_date = datetime.now()
        
        # --- UPDATED: Changed from days=2 to days=90 ---
        # Tells NewsAPI to search the last 3 months of news archives
        start_date = end_date - timedelta(days=90)
        
        params = {
            "q": query_string, 
            "from": start_date.strftime("%Y-%m-%d"), 
            "to": end_date.strftime("%Y-%m-%d"), 
            "language": "en", 
            "sortBy": "publishedAt", 
            "apiKey": NEWS_API_KEY, 
            "pageSize": 100 # Increased page size to grab more history in one go
        }
        try:
            print(f"📡 Querying NewsAPI for '{query_string}' (90-Day Window)...")
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = requests.get(NEWS_BASE_URL, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                articles = response.json().get("articles", [])
                for article in articles:
                    raw_date = article.get("publishedAt", "")
                    clean_date = raw_date[:19].replace('T', ' ') if len(raw_date) >= 19 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    headline = article.get("title", "")
                    description = article.get("description", "")
                    url_link = article.get("url", "")
                    source = article.get("source", {}).get("name", "Unknown")
                    
                    assigned_ticker = strict_classify_headline(headline)
                    if assigned_ticker:
                        if normalize_and_store(assigned_ticker, headline, description, url_link, clean_date, source):
                            api_saved += 1
            # Explicitly warn you in the logs if your API key tier blocks the 90-day request
            elif response.status_code == 426:
                print("⚠️ NewsAPI Error 426: Your API key tier does not support a 90-day lookback window (capped at 30 days).")
        except Exception as e:
            print(f"❌ API Error: {e}")

    total = rss_saved + api_saved
    if total > 0:
        print(f"🎯 Dual-Intake Complete: Saved {total} unique, verified articles ({rss_saved} Web, {api_saved} API).")


def requires_news_api_call(ticker, cooldown_hours=3):
    if not os.path.exists(DB_PATH): return True
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(published_at) FROM raw_news WHERE ticker = ?', (ticker,))
    latest_date = cursor.fetchone()[0]
    conn.close()

    if not latest_date: return True
    try:
        clean_time_str = latest_date[:19].replace('T', ' ')
        latest_dt = datetime.strptime(clean_time_str, "%Y-%m-%d %H:%M:%S")
        if (datetime.utcnow() - latest_dt) > timedelta(hours=cooldown_hours): return True
    except Exception:
        return True
    return False