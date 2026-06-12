# data/news_fetcher.py
import os
import re
import sqlite3
import requests
import spacy
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import random
import sys
import feedparser 
from src.config import TICKER_ALIASES, DB_PATH, NEWS_BASE_URL, RSS_FEEDS, USER_AGENTS

# Pull configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# --- SPACY NLP ENGINE INITIALIZATION ---
print("🧠 Initializing spaCy NLP Engine for Contextual News Filtering...")
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("⏳ Downloading spaCy 'en_core_web_sm' model (first-time setup)...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
print("✅ spaCy NLP Engine ready.")


def init_db():
    """Initializes the unified SQLite database schema."""
    conn = sqlite3.connect(DB_PATH)
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
    """
    HYBRID NLP TAGGER: 
    Uses fast Regex for unambiguous names ("Infosys", "RIL", "Reliance Industries").
    Deploys spaCy NLP ONLY to disambiguate common dictionary words like "Reliance".
    """
    if not headline:
        return None
        
    headline_lower = headline.lower()
    doc = None
    
    for ticker, patterns in TICKER_ALIASES.items():
        for pattern in patterns:
            match = re.search(pattern, headline_lower)
            if match:
                matched_text = match.group(0)
                
                # 1. Unambiguous matches (Trusted immediately without NLP)
                if matched_text != "reliance":
                    return ticker
                    
                # 2. Ambiguous match: "reliance"
                if doc is None:
                    doc = nlp(headline)
                    
                for token in doc:
                    if token.text.lower() == "reliance":
                        # CONDITION A: spaCy officially recognizes it as a Proper Noun or Entity
                        if token.pos_ == "PROPN" or token.ent_type_ in ["ORG", "PERSON", "PRODUCT", "GPE"]:
                            return ticker
                            
                        # CONDITION B: spaCy small-model fallback logic
                        if token.text == "Reliance":
                            prev_token = doc[token.i - 1].text.lower() if token.i > 0 else ""
                            blacklist = ["us", "heavy", "over", "on", "reduce", "increased", "their", "more"]
                            if prev_token not in blacklist:
                                return ticker
                
    return None 


def normalize_and_store(assigned_ticker, headline, description, url_link, published_at, source):
    """
    NORMALIZATION GATEWAY (Micro-Transaction):
    Opens a lightning-fast connection, checks for duplicates, saves, and closes instantly.
    This guarantees the database is NEVER locked while the scraper is sleeping.
    """
    # Open a brief connection with a 30-second timeout
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    
    # Check for duplicates based on URL or Exact Headline
    cursor.execute('''
        SELECT id FROM raw_news 
        WHERE url = ? OR headline = ?
    ''', (url_link, headline))
    
    if cursor.fetchone():
        conn.close()
        return False # Duplicate found! Reject it.
        
    try:
        cursor.execute('''
            INSERT INTO raw_news (ticker, headline, description, url, published_at, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (assigned_ticker, headline, description, url_link, published_at, source))
        
        # Commit the save IMMEDIATELY to release the database write-lock
        conn.commit() 
        conn.close()
        return True 
        
    except sqlite3.IntegrityError:
        conn.close()
        return False


def fetch_rss_news():
    """Scrapes raw XML/RSS feeds from the web safely using Anti-Ban mechanics."""
    print("🕸️ Scraping live RSS web feeds (Anti-Ban Active)...")
    inserted_count = 0
    
    # Define our strict cutoff time to only process recent news
    cutoff_time = datetime.now() - timedelta(days=2)
    
    for feed_url in RSS_FEEDS:
        try:
            # 1. THE DISGUISE: Pick a random web browser profile
            current_agent = random.choice(USER_AGENTS)
            feedparser.USER_AGENT = current_agent
            
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                # 2. STRICT DATE FILTERING
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    from time import mktime
                    entry_dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    if entry_dt < cutoff_time:
                        continue 
                
                headline = entry.get("title", "")
                description = entry.get("summary", "")
                url_link = entry.get("link", "")
                published_at = entry.get("published", datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
                source = feed.feed.get("title", "RSS Scraper")
                
                assigned_ticker = strict_classify_headline(headline)
                if assigned_ticker:
                    if normalize_and_store(assigned_ticker, headline, description, url_link, published_at, source):
                        inserted_count += 1
                        
            # 3. POLITENESS DELAY: Sleep randomly to avoid server rate limits
            sleep_time = random.uniform(2.0, 5.0)
            print(f"   [Sleeping for {sleep_time:.1f}s to avoid rate limits...]")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"⚠️ RSS Scrape Error for {feed_url}: {e}")
            
    return inserted_count


def fetch_and_store_news(query_string):
    """
    DUAL-INTAKE PIPELINE: 
    1. Scrapes from Web RSS
    2. Fetches from NewsAPI
    3. Normalizes and stores unified results.
    """
    # --- INTAKE 1: RSS WEB SCRAPING ---
    rss_saved = fetch_rss_news()
    
    # --- INTAKE 2: API FETCHING ---
    api_saved = 0
    if NEWS_API_KEY and NEWS_API_KEY != "YOUR_NEWS_API_KEY_HERE":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2)
        params = {
            "q": query_string, "from": start_date.strftime("%Y-%m-%d"), 
            "to": end_date.strftime("%Y-%m-%d"), "language": "en", 
            "sortBy": "publishedAt", "apiKey": NEWS_API_KEY, "pageSize": 50 
        }
        try:
            print(f"📡 Querying NewsAPI for '{query_string}'...")
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = requests.get(NEWS_BASE_URL, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                articles = response.json().get("articles", [])
                for article in articles:
                    headline = article.get("title", "")
                    description = article.get("description", "")
                    url_link = article.get("url", "")
                    published_at = article.get("publishedAt", "")
                    source = article.get("source", {}).get("name", "Unknown")
                    
                    assigned_ticker = strict_classify_headline(headline)
                    if assigned_ticker:
                        if normalize_and_store(assigned_ticker, headline, description, url_link, published_at, source):
                            api_saved += 1
        except Exception as e:
            print(f"❌ API Error: {e}")

    total = rss_saved + api_saved
    if total > 0:
        print(f"🎯 Dual-Intake Complete: Saved {total} unique, verified articles ({rss_saved} Web, {api_saved} API).")


def requires_news_api_call(ticker, cooldown_hours=3):
    """Checks if we need to hit the web or if we have recent data."""
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