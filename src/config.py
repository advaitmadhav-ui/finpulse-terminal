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
