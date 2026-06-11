# src/config.py
import os 

# Safe Configuration Variables
DB_PATH = "finpulse.db" 
NEWS_BASE_URL = "https://newsapi.org/v2/everything"

# Maps UI labels to Yahoo Finance tickers
TICKER_MAP = {
    "Reliance Industries": "RELIANCE.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Infosys": "INFY.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Kotak Mahindra": "KOTAKBANK.NS",
    "State Bank of India": "SBIN.NS",
    "Adani Enterprises": "ADANIENT.NS"
}

# --- NEW STRICT CLASSIFICATION MAPPING ---
# Uses Regex Word Boundaries (\b) so "SBI" doesn't match words containing 'sbi'
TICKER_ALIASES = {
    "RELIANCE.NS": [r"\breliance industries\b", r"\bril\b", r"\breliance\b"],
    "HDFCBANK.NS": [r"\bhdfc bank\b", r"\bhdfc\b"],
    "ICICIBANK.NS": [r"\bicici bank\b", r"\bicici\b"],
    "INFY.NS": [r"\binfosys\b", r"\binfy\b"],
    "TCS.NS": [r"\btcs\b", r"\btata consultancy services\b", r"\btata consultancy\b"],
    "KOTAKBANK.NS": [r"\bkotak mahindra\b", r"\bkotak bank\b", r"\bkotak\b"],
    "SBIN.NS": [r"\bsbi\b", r"\bstate bank of india\b", r"\bstate bank\b"],
    "ADANIENT.NS": [r"\badani enterprises\b", r"\badani group\b", r"\badani\b"]
}

REVERSE_TICKER_MAP = {v: k.upper() for k, v in TICKER_MAP.items()}

# These are live RSS feeds for Indian Financial Markets
RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/19770215.cms", 
    "https://economictimes.indiatimes.com/news/company/rssfeeds/2146843.cms",
    "https://www.livemint.com/rss/markets",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.moneycontrol.com/rss/business.xml",
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://www.business-standard.com/rss/companies-101.rss",
    "https://www.thehindubusinessline.com/markets/feeder/default.rss",
    "https://www.financialexpress.com/market/feed/",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=RELIANCE.NS,HDFCBANK.NS,ICICIBANK.NS,INFY.NS,TCS.NS,KOTAKBANK.NS,SBIN.NS,ADANIENT.NS"
]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]