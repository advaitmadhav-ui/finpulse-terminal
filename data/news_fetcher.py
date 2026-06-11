# data/news_fetcher.py
import os
import re
import sqlite3
import requests
import spacy
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Pull configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_ALIASES, DB_PATH, NEWS_BASE_URL

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
                # "RIL", "Reliance Industries", "HDFC" cannot be common nouns.
                if matched_text != "reliance":
                    return ticker
                    
                # 2. Ambiguous match: "reliance"
                # We deploy spaCy here to ensure it's not being used as a common noun 
                # (e.g., "China to reduce US reliance")
                if doc is None:
                    doc = nlp(headline)
                    
                for token in doc:
                    if token.text.lower() == "reliance":
                        # CONDITION A: spaCy officially recognizes it as a Proper Noun or Entity
                        if token.pos_ == "PROPN" or token.ent_type_ in ["ORG", "PERSON", "PRODUCT", "GPE"]:
                            return ticker
                            
                        # CONDITION B: spaCy small-model fallback logic
                        # If spaCy accidentally tags it as a standard noun, we verify its context.
                        # If it is Capitalized AND not preceded by context words that indicate
                        # the common dictionary noun (like "US reliance" or "heavy reliance").
                        if token.text == "Reliance":
                            prev_token = doc[token.i - 1].text.lower() if token.i > 0 else ""
                            blacklist = ["us", "heavy", "over", "on", "reduce", "increased", "their", "more"]
                            if prev_token not in blacklist:
                                return ticker
                
                # If we get here, it was lowercase "reliance" acting as a common noun.
                # We reject this and loop continues (just in case another ticker is in the headline)
                
    return None 

def fetch_and_store_news(query_string):
    """Fetches, contextually filters, and stores verified news."""
    if not NEWS_API_KEY or NEWS_API_KEY == "":
        print("❌ Error: NEWS_API_KEY is missing.")
        return

    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    
    params = {
        "q": query_string,
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY,
        "pageSize": 50 
    }

    try:
        response = requests.get(NEWS_BASE_URL, params=params, timeout=10)
        if response.status_code != 200:
            print(f"NewsAPI Error: {response.status_code} - {response.text}")
            return

        articles = response.json().get("articles", [])
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        inserted_count = 0
        for article in articles:
            headline = article.get("title", "")
            description = article.get("description", "")
            url_link = article.get("url", "")
            published_at = article.get("publishedAt", "")
            source = article.get("source", {}).get("name", "Unknown")
            
            # --- APPLY HYBRID CLASSIFICATION ---
            assigned_ticker = strict_classify_headline(headline)
            
            if assigned_ticker:
                try:
                    cursor.execute('''
                        INSERT INTO raw_news (ticker, headline, description, url, published_at, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (assigned_ticker, headline, description, url_link, published_at, source))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    pass 
                    
        conn.commit()
        conn.close()
        print(f"🎯 NLP Filter: Fetched query '{query_string}' -> Classified & Saved {inserted_count} verified articles.")
        
    except Exception as e:
        print(f"❌ Error fetching news: {e}")

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