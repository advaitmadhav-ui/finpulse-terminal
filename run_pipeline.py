# run_pipeline.py
import os
import sys
from dotenv import load_dotenv

# Force load environment variables
load_dotenv()

# Import the new strict fetching logic and config
from src.config import TICKER_ALIASES
from data.news_fetcher import init_db, fetch_and_store_news, requires_news_api_call

# Optional: Import Sentiment Analyzer if you want to score them immediately
from src.processing.sentiment_analyzer import process_pending_news 

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================

if __name__ == "__main__":
    print("🔄 Background Pipeline Auto-Triggered...")
    
    # 1. Ensure unified DB exists
    init_db()
    
    # 2. Extract general search queries from our alias list to cast a wide net
    # We will fetch news using these broad terms, but the STRICT CLASSIFIER 
    # inside fetch_and_store_news will guarantee they map perfectly to the ticker.
    queries_to_fetch = [
        "Reliance", "HDFC", "ICICI", "Infosys", "TCS", "Kotak", "State Bank", "Adani"
    ]
    
    # 3. Fetch and strictly Classify
    for query in queries_to_fetch:
        print(f"📡 Sweeping news stream for broad query: '{query}'...")
        fetch_and_store_news(query_string=query)
            
    # 4. Score the freshly fetched and strictly classified headlines
    print("🧠 Starting sentiment evaluation on new unclassified headlines...")
    try:
        process_pending_news()
    except Exception as e:
        print(f"⚠️ Sentiment analyzer failed or is not ready: {e}")

    print("🏁 Pipeline execution complete. Database is updated with strict matching.")