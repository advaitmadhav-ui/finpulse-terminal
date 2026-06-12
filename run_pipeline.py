# run_pipeline.py
import os
import sys
from dotenv import load_dotenv

# Fix paths to find the configuration module safely
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.config import TICKER_MAP
from src.ingestion.price_fetcher import fetch_and_store_prices, requires_price_update, init_price_table
from data.news_fetcher import fetch_and_store_news, requires_news_api_call, init_db
from src.processing.sentiment_analyzer import process_pending_news
from src.processing.data_aligner import align_ticker_data

# Load environment variables (API Keys, etc.)
load_dotenv()

def run_full_system_sync():
    print("🚀 Starting FinPulse System-Wide Synchronization...")
    
    # 1. Ensure core database schemas exist before doing anything
    init_db()
    init_price_table()
    
    updated_tickers = []
    
    # 2. Iterate through all tracked companies configured in src/config.py
    for keyword, ticker in TICKER_MAP.items():
        print(f"\n--- Checking {ticker} ({keyword}) ---")
        
        # Check independent cooldown timers
        needs_price = requires_price_update(ticker, cooldown_minutes=15)
        needs_news = requires_news_api_call(ticker, cooldown_hours=3)
        
        if needs_price or needs_news:
            updated_tickers.append(ticker)
            
            # Pull Prices (15-minute interval check)
            if needs_price:
                fetch_and_store_prices(ticker, period="60d", interval="15m")
            else:
                print(f"⏭️ Price data for {ticker} is fresh. Skipping.")
                
            # Pull News via API and Web Scraper (3-hour interval check)
            if needs_news:
                fetch_and_store_news(query_string=keyword)
            else:
                print(f"⏭️ News data for {ticker} is fresh. Skipping.")
        else:
            print(f"⏭️ All data for {ticker} is fresh. Skipping completely.")

    # 3. Batch Process AI Sentiment
    if updated_tickers:
        print("\n🧠 Running FinBERT Sentiment Analysis on new articles...")
        try:
            process_pending_news()
        except Exception as e:
            print(f"⚠️ Sentiment analyzer failed: {e}")
            
        # 4. Re-Align Time Series Data
        print("\n🔗 Aligning updated price and sentiment data for charts...")
        for ticker in updated_tickers:
            try:
                align_ticker_data(ticker)
            except Exception as e:
                print(f"⚠️ Data aligner failed for {ticker}: {e}")
                
        print("\n✅ System-Wide Synchronization Complete!")
    else:
        print("\n✅ System is fully up-to-date. No new data to process.")

if __name__ == "__main__":
    run_full_system_sync()