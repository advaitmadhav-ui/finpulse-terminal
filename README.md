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

## 📂 Project Structure
