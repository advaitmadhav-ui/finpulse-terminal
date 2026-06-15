# src/config.py
import os 

# Safe Configuration Variables
DB_PATH = "finpulse.db" 
NEWS_BASE_URL = "https://newsapi.org/v2/everything"

# src/config.py

# 1. THE TICKER MAP (Used by Yahoo Finance)
TICKER_MAP = {
    # Banking
    "HDFC Bank": "HDFCBANK.NS",
    "State Bank of India": "SBIN.NS",
    
    # Retail
    "Trent": "TRENT.NS",
    "DMart": "DMART.NS",
    
    # Manufacturing
    "Siemens India": "SIEMENS.NS",
    "ABB India": "ABB.NS",
    
    # Automobile
    "Maruti Suzuki": "MARUTI.NS",
    "Mahindra & Mahindra": "M&M.NS",
    
    # Global Tech (No .NS suffix because they trade on the NASDAQ in the US)
    "Microsoft": "MSFT",
    "NVIDIA": "NVDA"
}

# 2. THE NLP BOUNCER ALIASES (Must be strictly lowercase)
# These regex patterns ensure the NLP engine catches various ways news sites write the names.
TICKER_ALIASES = {
    "HDFCBANK.NS": [r"\bhdfc\b", r"\bhdfc bank\b"],
    "SBIN.NS": [r"\bsbi\b", r"\bstate bank of india\b", r"\bstate bank\b"],
    "TRENT.NS": [r"\btrent\b", r"\btrent limited\b"],
    "DMART.NS": [r"\bdmart\b", r"\bd-mart\b", r"\bavenue supermarts\b"],
    "SIEMENS.NS": [r"\bsiemens\b"],
    "ABB.NS": [r"\babb\b", r"\babb india\b"],
    "MARUTI.NS": [r"\bmaruti\b", r"\bmaruti suzuki\b"],
    "M&M.NS": [r"\bmahindra\b", r"\bm&m\b", r"\bmahindra & mahindra\b"],
    "MSFT": [r"\bmicrosoft\b", r"\bmsft\b"],
    "NVDA": [r"\bnvidia\b", r"\bnvda\b"]
}

REVERSE_TICKER_MAP = {v: k.upper() for k, v in TICKER_MAP.items()}

# These are live RSS feeds for Indian Financial Markets
# src/config.py


# src/config.py

RSS_FEEDS = {
    "HDFC Bank": [
        "https://news.google.com/rss/search?q=HDFC+Bank+stock+when:1y&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.moneycontrol.com/rss/mcfeed.xml",
        "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/21468428.cms"
    ],
    "State Bank of India": [
        "https://news.google.com/rss/search?q=State+Bank+of+India+SBI+stock+when:1y&hl=en-IN&gl=IN&ceid=IN:en",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SBIN.NS&region=IN&lang=en-IN",
        "https://www.moneycontrol.com/rss/business.xml"
    ], 
    "DMart": [
        "https://news.google.com/rss/search?q=Avenue+Supermarts+DMart+stock+when:1y&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.moneycontrol.com/rss/business.xml"
    ],
    "Siemens": [
        "https://news.google.com/rss/search?q=Siemens+India+stock+when:1y&hl=en-IN&gl=IN&ceid=IN:en",
        "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/21468428.cms"
    ],
    "ABB India": [
        "https://news.google.com/rss/search?q=ABB+India+stock+when:1y&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.moneycontrol.com/rss/business.xml"
    ],
    "Maruti Suzuki": [
        "https://news.google.com/rss/search?q=Maruti+Suzuki+stock+when:1y&hl=en-IN&gl=IN&ceid=IN:en",
        "https://auto.economictimes.indiatimes.com/rss/feed"
    ],
    "M&M": [
        "https://news.google.com/rss/search?q=Mahindra+and+Mahindra+stock+when:1y&hl=en-IN&gl=IN&ceid=IN:en",
        "https://www.moneycontrol.com/rss/business.xml"
    ],
    "Microsoft": [
        "https://news.google.com/rss/search?q=Microsoft+MSFT+stock+when:1y&hl=en-US&gl=US&ceid=US:en",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MSFT&region=US&lang=en-US"
    ],
    "NVIDIA": [
        "https://news.google.com/rss/search?q=NVIDIA+NVDA+stock+when:1y&hl=en-US&gl=US&ceid=US:en",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US"
    ]
}
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]