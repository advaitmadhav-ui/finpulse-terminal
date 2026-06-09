# FinPulse 📈
**A Quantamental Stock Analysis Dashboard**

FinPulse is an automated, real-time dashboard that combines historical financial market data with AI-driven sentiment analysis. By tracking asset prices and scoring the sentiment of recent news headlines using FinBERT, FinPulse provides a holistic "quantamental" view of the market, helping users identify bullish and bearish trends.

## 🚀 Features
* **Interactive Dashboard:** Built with Streamlit, featuring dynamic Plotly line charts and donut charts.
* **Multi-Stock Comparison:** Compare up to 8 major Indian equities simultaneously.
* **AI Sentiment Analysis:** Uses a locally run FinBERT Transformer model to score news headlines as Positive, Negative, or Neutral, generating AI recommendations (Buy/Sell/Hold).
* **On-Demand Background Sync:** FastAPI backend intelligently triggers data updates in the background when a user views a stock, preventing UI freezing.
* **Smart API Rate Limiting:** Implements a "Cooldown Shield" to prevent hitting NewsAPI daily limits.
* **Self-Healing Database:** Thread-safe SQLite database automatically initializes missing tables and handles concurrent background worker writes.

## 🏗️ Architecture & Tech Stack
* **Frontend:** Streamlit, Plotly Graph Objects / Express
* **Backend:** FastAPI, Uvicorn, BackgroundTasks
* **Database:** SQLite (`finpulse.db`)
* **Data Sources:** * `yfinance` (15m historical price candles)
  * NewsAPI (5-day rolling headline fetcher)
* **AI / ML:** Hugging Face `transformers` (FinBERT)
* **Data Processing:** Pandas

## 📂 Project Structure
```text
FP/
├── .env                        # Environment variables (NewsAPI Key)
├── src/
│   ├── api/
│   │   └── app.py              # FastAPI core engine
│   ├── config.py               # Constants, ticker mappings, and DB paths
│   ├── ingestion/
│   │   └── price_fetcher.py    # yfinance scraper (self-healing tables)
│   └── processing/
│       ├── sentiment_analyzer.py # FinBERT scoring module
│       └── data_aligner.py     # Analytics & dataframe alignment
├── data/
│   └── news_fetcher.py         # NewsAPI integration and raw_news schema
├── ui/
│   ├── app.py                  # Main Streamlit entry point
│   └── pages/
│       └── Compare_Stocks.py # Multi-stock comparison & sentiment panels
└── README.md
