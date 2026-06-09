# src/config.py
import os

# Database Path
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../finpulse.db"))

# Ticker Mapping: Maps common news keywords to official yfinance symbols (.NS for National Stock Exchange)
TICKER_MAP = {
    "Reliance Industries": "RELIANCE.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Infosys": "INFY.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Kotak Mahindra": "KOTAKBANK.NS",
    "State Bank of India": "SBIN.NS",
    "Adani Enterprises": "ADANIENT.NS"  # <-- Added Adani
}

# Maps the NewsAPI search keywords to the official Yahoo Finance tickers
KEYWORD_MAP = {
    "reliance": "RELIANCE.NS",
    "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "infosys": "INFY.NS",
    "tcs": "TCS.NS",
    "kotak": "KOTAKBANK.NS",
    "sbi": "SBIN.NS",
    "adani": "ADANIENT.NS"  # <-- Added Adani reverse mapping
}

# Inverse map for easy lookups in UI titles
REVERSE_TICKER_MAP = {v: k.upper() for k, v in TICKER_MAP.items()}

# NewsAPI Configurations
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "8e8216ced6bd427aa0e0990635b25369")
NEWS_BASE_URL = "https://newsapi.org/v2/everything"