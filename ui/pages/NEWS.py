# ui/pages/NEWS.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os
import sys
from streamlit_autorefresh import st_autorefresh

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import TICKER_MAP

# ==========================================
# 0. CUSTOM CSS THEMING
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        /* Base Theme Adjustments */
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
        /* Smooth Borders and Backgrounds for Cards */
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            background-color: #111520 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        
        /* Metric Typography */
        div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700 !important; }
        div[data-testid="stMetricLabel"] { color: #8a92a6 !important; font-size: 14px !important; }
        
        /* Selectbox and Input styling */
        .stSelectbox div[data-baseweb="select"], .stTextInput input {
            background-color: #111520 !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
            color: white !important;
        }
        
        /* Pills styling */
        .stPills [data-testid="stMarkdownContainer"] {
            font-size: 13px !important;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Live update feed loop every 90 seconds
st_autorefresh(interval=90000, limit=500, key="global_news_refresh")

# ==========================================
# 1. PAGE HEADER
# ==========================================
st.markdown("## 📰 Market News Feed")
st.markdown("<span style='color: gray; font-size: 14px;'>Track top assets, analyze macro trends, and uncover market opportunities.</span>", unsafe_allow_html=True)
st.write("")

# ==========================================
# 2. DATA PIPELINE
# ==========================================
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
    df['Event_Time'] = pd.to_datetime(df['Event_Time'], errors='coerce')
    df = df.drop_duplicates(subset=['Headline', 'Event_Time'])
    df = df.sort_values(by='Event_Time', ascending=False)
    return df

news_df = fetch_all_market_news()

# ==========================================
# 3. CHART & UI HELPERS
# ==========================================
def create_sentiment_gauge(score):
    """Generates a compact gauge chart for the top card."""
    normalized_val = ((score + 1) / 2) * 100
    color = "#22ab59" if score > 0.05 else "#ea5455" if score < -0.05 else "#7f7f7f"

    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=normalized_val,
        number={'font': {'size': 36, 'color': 'white'}, 'valueformat': ".0f"},
        gauge={
            'axis': {'range': [0, 100], 'visible': False},
            'bar': {'color': color, 'thickness': 0.8},
            'bgcolor': "rgba(255,255,255,0.05)", 'shape': "angular"
        }
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=140, paper_bgcolor='rgba(0,0,0,0)')
    return fig

def create_volume_bar_chart(df, color):
    """Generates a sparkline bar chart showing volume over recent days."""
    if df.empty: return go.Figure()
    
    # Group by date for the sparkline
    df['DateOnly'] = df['Event_Time'].dt.date
    daily_vol = df.groupby('DateOnly').size().tail(10)
    
    fig = go.Figure(go.Bar(x=daily_vol.index, y=daily_vol.values, marker_color=color, opacity=0.8))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=50,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False, hovermode=False
    )
    return fig

# ==========================================
# 4. MAIN DASHBOARD RENDER
# ==========================================
if news_df.empty:
    st.info("⏳ Awaiting active data feeds. Ensure your FastAPI server backend pipelines are running.")
else:
    # Calculate Macro Metrics
    total_stories = len(news_df)
    pos_df = news_df[news_df['Sentiment'] > 0.05]
    neg_df = news_df[news_df['Sentiment'] < -0.05]
    neu_df = news_df[(news_df['Sentiment'] >= -0.05) & (news_df['Sentiment'] <= 0.05)]
    
    bullish_count, bearish_count, neutral_count = len(pos_df), len(neg_df), len(neu_df)
    avg_sentiment = news_df['Sentiment'].mean()
         
    if avg_sentiment > 0.15: mood_str, mood_color = "STRONGLY BULLISH", "#22ab59"
    elif avg_sentiment > 0.02: mood_str, mood_color = "MILDLY BULLISH", "#22ab59"
    elif avg_sentiment < -0.15: mood_str, mood_color = "STRONGLY BEARISH", "#ea5455"
    elif avg_sentiment < -0.02: mood_str, mood_color = "MILDLY BEARISH", "#ea5455"
    else: mood_str, mood_color = "NEUTRAL / RANGE", "#7f7f7f"

    # --- TOP MACRO METRICS BAR ---
    m_col1, m_col2, m_col3, m_col4 = st.columns([2.2, 1, 1, 1])
    
    with m_col1:
        with st.container(border=True):
            st.markdown("<div style='color: #8a92a6; font-size: 14px; margin-bottom: -10px;'>Market Sentiment Index</div>", unsafe_allow_html=True)
            g1, g2 = st.columns([1, 1.2])
            with g1:
                st.plotly_chart(create_sentiment_gauge(avg_sentiment), use_container_width=True, config={'displayModeBar': False})
            with g2:
                st.write("")
                st.markdown(f"<div style='color: {mood_color}; font-size: 20px; font-weight: bold; margin-bottom: 15px;'>{mood_str}</div>", unsafe_allow_html=True)
                
                # Advancing / Declining numbers
                s1, s2, s3 = st.columns(3)
                with s1:
                    st.markdown("<div style='font-size: 11px; color: gray;'>Advancing</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 14px; color: #22ab59; font-weight: bold;'>{bullish_count}</div>", unsafe_allow_html=True)
                with s2:
                    st.markdown("<div style='font-size: 11px; color: gray;'>Declining</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 14px; color: #ea5455; font-weight: bold;'>{bearish_count}</div>", unsafe_allow_html=True)
                with s3:
                    st.markdown("<div style='font-size: 11px; color: gray;'>Unchanged</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 14px; color: gray; font-weight: bold;'>{neutral_count}</div>", unsafe_allow_html=True)

    with m_col2:
        with st.container(border=True):
            st.metric("Bullish Volume", f"{bullish_count}", f"{((bullish_count/total_stories)*100):.0f}%")
            st.plotly_chart(create_volume_bar_chart(pos_df, "#22ab59"), use_container_width=True, config={'displayModeBar': False})

    with m_col3:
        with st.container(border=True):
            st.metric("Bearish Volume", f"{bearish_count}", f"-{((bearish_count/total_stories)*100):.0f}%", delta_color="inverse")
            st.plotly_chart(create_volume_bar_chart(neg_df, "#ea5455"), use_container_width=True, config={'displayModeBar': False})

    with m_col4:
        with st.container(border=True):
            st.metric("Total Stream Volume", f"{total_stories} items")
            st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True) # Spacer to match height

    st.write("---")

    # --- FILTER TERMINAL ROW ---
    f_col1, f_col2, f_col3 = st.columns([1.2, 1.5, 2])
    with f_col1:
        selected_asset = st.selectbox("Filter Asset", options=["All Tracked Assets"] + list(TICKER_MAP.keys()), label_visibility="collapsed")
    with f_col2:
        sentiment_filter = st.pills("Filter Sentiment", options=["All", "Bullish", "Bearish", "Neutral"], default="All", label_visibility="collapsed")
    with f_col3:
        search_query = st.text_input("Search Headlines", placeholder="Search keywords (e.g., earnings)...", label_visibility="collapsed")

    # --- APPLY FILTER LOGIC ---
    filtered_df = news_df.copy()
    if selected_asset != "All Tracked Assets": filtered_df = filtered_df[filtered_df['Asset_Label'] == selected_asset]
    if sentiment_filter == "Bullish": filtered_df = filtered_df[filtered_df['Sentiment'] > 0.05]
    elif sentiment_filter == "Bearish": filtered_df = filtered_df[filtered_df['Sentiment'] < -0.05]
    elif sentiment_filter == "Neutral": filtered_df = filtered_df[(filtered_df['Sentiment'] >= -0.05) & (filtered_df['Sentiment'] <= 0.05)]
    if search_query: filtered_df = filtered_df[filtered_df['Headline'].str.contains(search_query, case=False, na=False)]
    
    st.write("") 

    # --- CLEAN UNIFORM STREAM VIEW ---
    if filtered_df.empty:
        st.info("No modern headlines match your target criteria.")
    else:
        st.markdown("### News Feed")
        with st.container(border=True):
            for _, row in filtered_df.iterrows():
                score = float(row["Sentiment"])
                headline = row["Headline"]
                timestamp = row["Event_Time"].strftime("%Y-%m-%d") if pd.notnull(row["Event_Time"]) else "Unknown Date"
                source = row.get("Source", "Market Feed")
                asset_tag = row["Asset_Label"]
                                 
                if score > 0.05:
                    badge_color = "#22ab59"
                    bg_color = "rgba(34, 171, 89, 0.1)"
                elif score < -0.05:
                    badge_color = "#ea5455"
                    bg_color = "rgba(234, 84, 85, 0.1)"
                else:
                    badge_color = "#7f7f7f"
                    bg_color = "rgba(127, 127, 127, 0.1)"
                                 
                row_col1, row_col2, row_col3 = st.columns([1.2, 5.5, 1.3])
                                 
                with row_col1:
                    # Sleek Asset Tag Box
                    st.markdown(f"""
                        <div style='background-color: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); display: inline-block; font-size: 13px; font-weight: 600;'>
                            {asset_tag}
                        </div>
                    """, unsafe_allow_html=True)
                                 
                with row_col2:
                    st.markdown(f"<div style='font-weight: 600; font-size: 15px; margin-bottom: 4px;'>{headline}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='color: gray; font-size: 12px;'>📅 {timestamp} | Source: {source}</div>", unsafe_allow_html=True)
                                     
                with row_col3:
                    # Pill-shaped Sentiment Badge with Signal Icon
                    st.markdown(f"""
                        <div style='background-color: {bg_color}; border: 1px solid {badge_color}; color: {badge_color}; padding: 6px 15px; border-radius: 20px; text-align: center; font-weight: 700; font-size: 14px; display: flex; justify-content: center; align-items: center; gap: 8px;'>
                            <span style='font-size: 12px;'>((•))</span> {score:+.2f}
                        </div>
                    """, unsafe_allow_html=True)
                                 
                st.markdown("<hr style='margin: 15px 0px; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)