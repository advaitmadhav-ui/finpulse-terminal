# FinPulse 📈
**A Quantamental Stock Analysis Dashboard**

## 📖 Project Overview
FinPulse is an automated, real-time dashboard that combines historical financial market data with AI-driven sentiment analysis. By tracking asset prices and scoring the sentiment of recent news headlines using a local FinBERT model, FinPulse provides a holistic "quantamental" view of the market, helping users identify bullish, bearish, and neutral trends for major Indian equities.

## 🏗️ Architecture Summary
FinPulse operates on a decoupled, two-tier architecture:
* **Frontend UI:** Built with **Streamlit**, featuring interactive Plotly charts for price comparison and donut charts for sentiment visualization.
* **Backend API:** Built with **FastAPI** and Uvicorn. It handles data fetching, AI processing, and serves as the central data hub.
* **Database:** A thread-safe, self-healing **SQLite** database (`finpulse.db`) stores historical prices and raw news to minimize API calls and prevent rate-limiting.
* **AI Engine:** Uses Hugging Face's `transformers` library to run the **FinBERT** model locally for financial sentiment classification.
* **Data Sources:** `yfinance` for market data and NewsAPI for financial headlines.

## ⚙️ Setup Instructions

### 1. Prerequisites
* Python 3.9 or higher installed on your system.
* Git installed.

### 2. Environment Setup
Clone the repository and navigate to the project root (`FP/`). Then, create and activate a virtual environment:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```
### 3. Install Dependencies
Install all required Python packages:
```bash
pip install fastapi uvicorn streamlit pandas yfinance plotly requests transformers torch python-dotenv
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and add your NewsAPI key. **Do not commit this file to version control.**
```env
NEWS_API_KEY=your_actual_api_key_here
```

### 5. Initialize the Database
Run the following command to build the necessary SQLite tables (`raw_news` and `historical_prices`):
```bash
python -c "from data.news_fetcher import init_db; init_db()"
```
## 🏃‍♂️ How to Run the Project
FinPulse requires both the backend and frontend to be running simultaneously in **two separate terminal windows**.

### Terminal 1: Start the Backend API
Ensure your virtual environment is activated, then start the FastAPI server:
```bash
uvicorn src.api.app:app --reload
```
*The backend API will boot up and listen for requests at `http://127.0.0.1:8000`*

### Terminal 2: Start the Frontend UI
Open a **second, completely separate terminal**, activate your virtual environment again, and launch the Streamlit app:
```bash
streamlit run ui/HOME_PAGE.py
```
*the front will boot up on a streamlit based ui and will have a different link from local host

## 📂 Project Structure
```text
FP/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                 # FastAPI core engine
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── price_fetcher.py       # yfinance scraper
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── data_aligner.py        # Analytics & dataframe alignment
│   │   └── sentiment_analyzer.py  # FinBERT scoring module
│   ├── __init__.py
│   └── config.py                  # Constants and database config
├── ui/
│   ├── pages/
│   │   ├── Compare_Stocks.py      # Multi-stock comparison & sentiment panels
│   │   ├── NEWS.py                # News feed module
│   │   └── SENTIMENT_ANALYTICS.py # Dedicated sentiment views
│   └── HOME_PAGE.py               # Main Streamlit entry point
├── .env                           # Environment variables (NewsAPI Key)
├── .env.example                   # Template for environment variables
├── finpulse.db                    # SQLite database (Self-healing)
└── README.md
```



