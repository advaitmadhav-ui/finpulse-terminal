# ui/market_news.py
import streamlit as st
import requests
import pandas as pd
import os
import sys
from streamlit_autorefresh import st_autorefresh

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_MAP

st.set_page_config(page_title="FinPulse | Market News", layout="wide")

# Live update feed loop every 90 seconds
st_autorefresh(interval=90000, limit=500, key="global_news_refresh")

# --- HEADER SECTION ---
st.title("Market News Feed")

# --- BACKEND DATA CONSUMER ---
@st.cache_data(ttl=30)
def fetch_all_market_news():
    aggregated_news = []
    for label, ticker in TICKER_MAP.items():
        API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{ticker}"
        try:
            response = requests.get(API_ENDPOINT, timeout=3)
            if response.status_code == 200:
                payload = response.json()
                raw_news = payload.get("recent_news", [])
                for item in raw_news:
                    item["Asset_Label"] = label
                    item["Ticker"] = ticker
                    aggregated_news.append(item)
        except Exception:
            continue
            
    if not aggregated_news:
        return pd.DataFrame()
        
    df = pd.DataFrame(aggregated_news)
    df['Sentiment'] = pd.to_numeric(df['Sentiment'], errors='coerce')
    df = df.drop_duplicates(subset=['Headline', 'Event_Time'])
    df = df.sort_values(by='Event_Time', ascending=False)
    return df

news_df = fetch_all_market_news()

if news_df.empty:
    st.info("🔌 Awaiting active data feeds. Ensure your FastAPI server backend pipelines are running.")
else:
    # --- CALCULATE METRICS ---
    total_stories = len(news_df)
    bullish_count = len(news_df[news_df['Sentiment'] > 0])
    bearish_count = len(news_df[news_df['Sentiment'] < 0])
    avg_sentiment = news_df['Sentiment'].mean()
    
    if avg_sentiment > 0.15:
        mood_str, mood_color = "STRONGLY BULLISH", "green"
    elif avg_sentiment > 0.02:
        mood_str, mood_color = "MILDLY BULLISH", "green"
    elif avg_sentiment < -0.15:
        mood_str, mood_color = "STRONGLY BEARISH", "red"
    elif avg_sentiment < -0.02:
        mood_str, mood_color = "MILDLY BEARISH", "red"
    else:
        mood_str, mood_color = "NEUTRAL / RANGEBOUND", "gray"

    # --- TOP MACRO METRICS BAR ---
    # Kept clean, purely numerical, and horizontally aligned
    m_col1, m_col2, m_col3, m_col4 = st.columns([3, 1, 1, 1])
    with m_col1:
        st.metric("Market Sentiment Index", mood_str)
    with m_col2:
        st.metric("Bullish Volume", f"{bullish_count}", f"{((bullish_count/total_stories)*100):.0f}%")
    with m_col3:
        st.metric("Bearish Volume", f"{bearish_count}", f"-{((bearish_count/total_stories)*100):.0f}%", delta_color="inverse")
    with m_col4:
        st.metric("Total Stream Volume", f"{total_stories} items")

    st.write("---")

    # --- FILTER TERMINAL ROW ---
    # Placed in a single horizontal bar right above the feed to maximize whitespace efficiency
    f_col1, f_col2, f_col3 = st.columns([1.2, 1.3, 2])
    with f_col1:
        selected_asset = st.selectbox(
            "Filter Asset", 
            options=["All Tracked Assets"] + list(TICKER_MAP.keys()),
            label_visibility="collapsed"
        )
    with f_col2:
        sentiment_filter = st.pills(
            "Filter Sentiment", 
            options=["All", "Bullish", "Bearish", "Neutral"], 
            default="All",
            label_visibility="collapsed"
        )
    with f_col3:
        search_query = st.text_input(
            "Search Headlines", 
            placeholder="Search keywords (e.g., earnings)...",
            label_visibility="collapsed"
        )

    # --- APPLY FILTER LOGIC ---
    filtered_df = news_df.copy()
    if selected_asset != "All Tracked Assets":
        filtered_df = filtered_df[filtered_df['Asset_Label'] == selected_asset]
    if sentiment_filter == "Bullish":
        filtered_df = filtered_df[filtered_df['Sentiment'] > 0]
    elif sentiment_filter == "Bearish":
        filtered_df = filtered_df[filtered_df['Sentiment'] < 0]
    elif sentiment_filter == "Neutral":
        filtered_df = filtered_df[filtered_df['Sentiment'] == 0]
    if search_query:
        filtered_df = filtered_df[filtered_df['Headline'].str.contains(search_query, case=False, na=False)]

    st.write("") # Spacer

    # --- CLEAN UNIFORM STREAM VIEW ---
    if filtered_df.empty:
        st.info("No modern headlines match your target criteria.")
    else:
        # A single outer scroll container without nested border cards inside
        with st.container(height=600, border=False):
            for _, row in filtered_df.iterrows():
                score = float(row["Sentiment"])
                headline = row["Headline"]
                timestamp = row["Event_Time"].split("T")[0] # Clean date format
                source = row.get("Source", "Market Feed")
                asset_tag = row["Asset_Label"]
                
                if score > 0:
                    badge = f"🟢 +{score:.2f}"
                elif score < 0:
                    badge = f"🔴 {score:.2f}"
                else:
                    badge = f"⚪  0.00"
                
                # Dynamic row grid layout for data scanning
                row_col1, row_col2, row_col3 = st.columns([0.8, 4, 1])
                
                with row_col1:
                    # Renders asset tracking unit clean
                    st.caption(f"`{asset_tag}`")
                
                with row_col2:
                    st.markdown(f"**{headline}**")
                    st.caption(f"{timestamp} | Source: {source}")
                    
                with row_col3:
                    # Aligned scorecard right-side terminal view
                    st.markdown(f"**{badge}**")
                
                st.markdown("<hr style='margin: 8px 0px; opacity: 0.15;'>", unsafe_allow_html=True)