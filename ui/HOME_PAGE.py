# ui/home.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os
import sys
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# Ensure the script can find the config file
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_MAP

st.set_page_config(page_title="FinPulse | Market Sentiment Tracker", layout="wide")

# Silently refresh the UI every 60 seconds to act as a live terminal
st_autorefresh(interval=60000, limit=500, key="live_market_refresh")

# ==========================================
# 1. MACRO OVERVIEW DATA PIPELINES
# ==========================================

@st.cache_data(ttl=60)
def fetch_watchlist_summary():
    """Fetches the latest price and sentiment for all tracked assets to build the landing page."""
    summary_data = []
    
    for label, ticker in TICKER_MAP.items():
        API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{ticker}"
        try:
            response = requests.get(API_ENDPOINT, timeout=2)
            if response.status_code == 200:
                payload = response.json()
                
                # Extract latest price data
                time_series = payload.get("time_series", [])
                if time_series:
                    df = pd.DataFrame(time_series)
                    df['datetime'] = pd.to_datetime(df['datetime_str'])
                    df = df.sort_values('datetime')
                    
                    latest_date = df['datetime'].dt.date.max()
                    today_df = df[df['datetime'].dt.date == latest_date]
                    prev_df = df[df['datetime'].dt.date < latest_date]
                    
                    current_price = today_df['close'].iloc[-1] if not today_df.empty else df['close'].iloc[-1]
                    prev_close = prev_df['close'].iloc[-1] if not prev_df.empty else current_price
                    
                    pct_change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0.0
                else:
                    current_price = 0.0
                    pct_change = 0.0

                # Extract latest sentiment
                recent_news = payload.get("recent_news", [])
                if recent_news:
                    avg_sentiment = pd.DataFrame(recent_news)['Sentiment'].astype(float).mean()
                else:
                    avg_sentiment = 0.0

                summary_data.append({
                    "Asset": label,
                    "Ticker": ticker,
                    "Price": current_price,
                    "Change": pct_change,
                    "Sentiment": avg_sentiment
                })
        except Exception:
            continue
            
    return summary_data

@st.cache_data(ttl=3600) 
def fetch_macro_leaderboard(timeframe):
    """Fetches historical returns across all tickers and sorts them from highest to lowest."""
    period_map = {"6M": "6mo", "1Y": "1y", "3Y": "3y"}
    yf_period = period_map.get(timeframe, "1y")
    
    leaderboard_data = []
    
    for label, ticker in TICKER_MAP.items():
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(period=yf_period)
            
            if not hist.empty:
                start_close = hist['Close'].iloc[0]
                end_close = hist['Close'].iloc[-1]
                
                total_return = ((end_close - start_close) / start_close) * 100 if start_close != 0 else 0.0
                
                leaderboard_data.append({
                    "Asset": label,
                    "Ticker": ticker,
                    "Current": end_close,
                    "Return": total_return
                })
        except Exception:
            continue
            
    return sorted(leaderboard_data, key=lambda x: x['Return'], reverse=True)


def render_overview_dashboard():
    """Renders a professional landing page with a clean 2x4 grid and a performance leaderboard."""
    st.markdown("### 🌐 Market Pulse Overview")
    st.markdown("Welcome to the FinPulse Terminal. Select an asset from the dropdown above for deep-dive analytics, or review the current macro snapshot below.")
    st.write("---")
    
    summary_data = fetch_watchlist_summary()
    
    if not summary_data:
        st.info("Loading asset data pipelines. Please wait for the backend to sync...")
        return
        
    # --- 2x4 MAIN METRICS GRID ---
    MAX_COLUMNS = 4
    for i in range(0, len(summary_data), MAX_COLUMNS):
        row_data = summary_data[i:i + MAX_COLUMNS]
        cols = st.columns(MAX_COLUMNS)
        
        for idx, data in enumerate(row_data):
            with cols[idx]:
                with st.container(border=True, height=210):
                    title_col, tag_col = st.columns([1.5, 1]) 
                    with title_col:
                        st.markdown(f"<div style='font-size: 1.1em; font-weight: 600; line-height: 1.2; padding-bottom: 5px;'>{data['Asset']}</div>", unsafe_allow_html=True)
                    with tag_col:
                        st.markdown(f"<div style='text-align: right;'><span style='color: gray; font-size: 10px; background-color: rgba(128,128,128,0.1); padding: 3px 6px; border-radius: 4px; word-break: break-all;'>{data['Ticker']}</span></div>", unsafe_allow_html=True)
                    
                    st.write("") 
                    
                    st.metric(
                        label="Current Value", 
                        value=f"₹{data['Price']:,.2f}", 
                        delta=f"{data['Change']:+.2f}%"
                    )
                    
                    if data['Sentiment'] > 0.05:
                        badge_html = "<span style='color: #22ab59; font-weight: bold;'>🟢 Bullish Bias</span>"
                    elif data['Sentiment'] < -0.05:
                        badge_html = "<span style='color: #ea5455; font-weight: bold;'>🔴 Bearish Bias</span>"
                    else:
                        badge_html = "<span style='color: gray; font-weight: bold;'>⚪ Neutral Range</span>"
                        
                    st.markdown(f"<div style='margin-top: 5px; font-size: 13px;'>{badge_html}</div>", unsafe_allow_html=True)

    st.write("")
    st.write("")

    # --- PERFORMANCE LEADERBOARD LIST ---
    st.write("---")
    
    lead_title_col, lead_toggle_col = st.columns([3, 1])
    
    with lead_title_col:
        st.markdown("### 🏆 Macro Returns Leaderboard")
        st.caption("Ranked absolute performance of watchlisted assets across historical macro windows.")
        
    with lead_toggle_col:
        selected_horizon = st.pills(
            "Select Timeframe Horizon",
            options=["6M", "1Y", "3Y"],
            default="1Y",
            label_visibility="collapsed",
            key="macro_leaderboard_toggle"
        )
        
    with st.spinner(f"Computing historical returns for window: {selected_horizon}..."):
        leaderboard_list = fetch_macro_leaderboard(selected_horizon)
        
    if not leaderboard_list:
        st.warning("Historical data parsing engines are initializing. Please verify network paths to data streams.")
        return

    st.write("")
    
    st.markdown("""
        <div style='display: flex; background-color: rgba(128,128,128,0.05); padding: 10px 15px; border-radius: 6px; font-weight: bold; font-size: 12px; color: gray;'>
            <div style='flex: 0.5;'>RANK</div>
            <div style='flex: 2;'>ASSET IDENTIFIER</div>
            <div style='flex: 1.5; text-align: right;'>LAST CLOSE</div>
            <div style='flex: 1.5; text-align: right;'>ACCUMULATED RETURNS</div>
        </div>
    """, unsafe_allow_html=True)

    for rank, item in enumerate(leaderboard_list, start=1):
        if item['Return'] >= 0:
            color_style = "color: #22ab59; font-weight: 600;"
            arrow_indicator = "▲"
        else:
            color_style = "color: #ea5455; font-weight: 600;"
            arrow_indicator = "▼"
            
        st.markdown(f"""
            <div style='display: flex; padding: 12px 15px; border-bottom: 1px solid rgba(128,128,128,0.1); font-size: 14px; align-items: center;'>
                <div style='flex: 0.5; font-weight: bold; color: gray;'>#{rank}</div>
                <div style='flex: 2; font-weight: 500;'>
                    {item['Asset']} <span style='font-size: 11px; color: gray; margin-left: 6px;'>({item['Ticker']})</span>
                </div>
                <div style='flex: 1.5; text-align: right; font-family: monospace;'>₹{item['Current']:,.2f}</div>
                <div style='flex: 1.5; text-align: right; {color_style}'>{arrow_indicator} {abs(item['Return']):.2f}%</div>
            </div>
        """, unsafe_allow_html=True)


# ==========================================
# 2. INDIVIDUAL ASSET DASHBOARD LOGIC
# ==========================================

def render_dynamic_stock_chart(time_series_data, ticker_name):
    """Renders the broker-style chart with dynamic scaling, live anchoring, and clean visible axes."""
    
    metric_col1, metric_col2, metric_col3, spacer, pill_col = st.columns([1.8, 1.8, 2.2, 0.2, 2.5])
    
    with pill_col:
        selected_period = st.pills(
            "Timeframe", 
            options=["1D", "1W", "1M", "2M", "1Y"], 
            default="1D",
            label_visibility="collapsed"
        )

    if selected_period == "1Y":
        with st.spinner("Fetching historical year data..."):
            try:
                raw_yf = yf.Ticker(ticker_name).history(period="1y", interval="1d")
                if raw_yf.empty:
                    st.error("Could not retrieve historical 1Y data from Yahoo Finance.")
                    return
                
                df_filtered = raw_yf.reset_index()
                df_filtered = df_filtered.rename(columns={'Date': 'datetime', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'})
                df_filtered['datetime'] = pd.to_datetime(df_filtered['datetime']).dt.tz_localize(None)
                start_price = df_filtered['close'].iloc[-1] if df_filtered.empty else df_filtered['close'].iloc[0]
            except Exception as e:
                st.error(f"Error connecting to historical data pipeline: {e}")
                return
    else:
        if not time_series_data:
            st.warning("No price data available to render the dashboard chart. (Waiting for background sync...)")
            return

        df = pd.DataFrame(time_series_data)
        df['datetime'] = pd.to_datetime(df['datetime_str'])
        df = df.sort_values('datetime')

        if selected_period == "1D":
            latest_date = df['datetime'].dt.date.max()
            df_filtered = df[df['datetime'].dt.date == latest_date]
            
            previous_days_df = df[df['datetime'].dt.date < latest_date]
            if not previous_days_df.empty:
                start_price = previous_days_df['close'].iloc[-1]
            else:
                start_price = df_filtered['close'].iloc[0]
                
        elif selected_period == "1W":
            df_filtered = df.tail(125).copy()
            start_price = df_filtered['close'].iloc[0]
            
        elif selected_period == "1M":
            latest_date = df['datetime'].dt.date.max()
            start_date = latest_date - pd.Timedelta(days=30)
            df_raw = df[df['datetime'].dt.date >= start_date].copy()
            
            df_raw['date_group'] = df_raw['datetime'].dt.date
            df_filtered = df_raw.groupby('date_group').agg({
                'datetime': 'last',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).reset_index()
            start_price = df_filtered['close'].iloc[0]
            
        elif selected_period == "2M": 
            df_raw = df.copy()
            df_raw['date_group'] = df_raw['datetime'].dt.date
            df_filtered = df_raw.groupby('date_group').agg({
                'datetime': 'last',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).reset_index()
            start_price = df_filtered['close'].iloc[0]

    if df_filtered.empty:
        st.info("Insufficient data points captured for this specific timeframe.")
        return

    period_high = df_filtered['high'].max()
    period_low = df_filtered['low'].min()
    end_price = df_filtered['close'].iloc[-1]
    
    true_high = max(period_high, start_price)
    true_low = min(period_low, start_price)
    
    spread = true_high - true_low
    if spread == 0:
        spread = true_high * 0.01  
        
    padding = spread * 0.25
    y_min = true_low - padding
    y_max = true_high + padding
    
    price_delta = end_price - start_price
    pct_change = (price_delta / start_price) * 100 if start_price != 0 else 0.0

    if price_delta >= 0:
        line_color = "#22ab59"      
        fill_color = "rgba(34, 171, 89, 0.15)"
        arrow = "▲"
    else:
        line_color = "#ea5455"      
        fill_color = "rgba(234, 84, 85, 0.15)"
        arrow = "▼"

    with metric_col1:
        st.metric("High", f"₹{period_high:,.2f}")
    with metric_col2:
        st.metric("Low", f"₹{period_low:,.2f}")
    with metric_col3:
        st.metric("Returns", f"{arrow} {abs(pct_change):.2f}%", delta=f"{price_delta:+.2f}")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_filtered['datetime'],
        y=df_filtered['close'],
        mode='lines',
        line=dict(color=line_color, width=2),
        fill='tozeroy',
        fillcolor=fill_color,
        hovertemplate="<b>₹ %{y:.2f}</b><br><span style='color:gray; font-size:12px;'>%{x|%b %d, %Y %I:%M %p}</span><extra></extra>"
    ))

    if selected_period == "1D":
        fig.add_hline(
            y=start_price, 
            line_dash="dot", 
            line_color="gray", 
            line_width=1.5, 
            opacity=0.6,
            annotation_text="Prev. Close", 
            annotation_position="bottom right",
            annotation_font_size=10,
            annotation_font_color="gray"
        )

    fig.update_layout(
        margin=dict(l=10, r=50, t=10, b=30), 
        height=400,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        
        xaxis=dict(
            showgrid=False, 
            zeroline=False, 
            showticklabels=True,      
            tickfont=dict(color="gray", size=10),
            showline=False,
            showspikes=True,      
            spikemode="across",
            spikesnap="cursor",
            spikedash="dot",
            spikecolor="#b3b3b3",
            spikethickness=1.5,
            rangebreaks=[
                dict(bounds=["sat", "mon"]),  
                dict(bounds=[15.5, 9.25], pattern="hour") if selected_period in ["1D", "1W"] else dict(values=[])
            ]
        ),
        
        yaxis=dict(
            showgrid=True,            
            gridcolor="rgba(128, 128, 128, 0.1)", 
            zeroline=False, 
            showticklabels=True,      
            tickfont=dict(color="gray", size=10),
            tickformat=",.0f",        
            side="right",             
            showline=False,
            autorange=False,      
            range=[y_min, y_max]  
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# ==========================================
# 3. MAIN PAGE ROUTING
# ==========================================

st.title("📊 FinPulse Dashboard")

selected_label = st.selectbox(
    "Select Asset Tracker:", 
    options=list(TICKER_MAP.keys()), 
    index=None,
    placeholder="Choose an asset to view its dashboard..."
)

if not selected_label:
    render_overview_dashboard()
    st.stop()

# Load individual dashboard if a ticker is selected
target_ticker = TICKER_MAP[selected_label]
API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{target_ticker}"

try:
    response = requests.get(API_ENDPOINT)
    if response.status_code == 200:
        payload = response.json()
        time_series = payload.get("time_series", [])
        recent_news = payload.get("recent_news", [])
        
        col1, col2 = st.columns([2.5, 1])
        
        with col1:
            render_dynamic_stock_chart(time_series, target_ticker)
                
        with col2:
            st.subheader("📰 Live Asset Sentiment Feed")
            if recent_news:
                with st.container(height=400):
                    for item in recent_news:
                        score = float(item["Sentiment"])
                        headline = item["Headline"]
                        timestamp = item["Event_Time"].replace("T", " ").replace("Z", "")
                        
                        if score > 0:
                            sentiment_tag = f"🟢 Bullish (+{score:.2f})"
                        elif score < 0:
                            sentiment_tag = f"🔴 Bearish ({score:.2f})"
                        else:
                            sentiment_tag = "⚪ Neutral (0.00)"
                            
                        with st.container(border=True):
                            st.caption(f"🕒 {timestamp} | {item['Source']}")
                            st.markdown(f"**{headline}**")
                            st.markdown(f"*Sentiment Indicator:* {sentiment_tag}")
            else:
                st.info("No evaluated news metrics match this tracking signature currently.")
    else:
        st.error(f"❌ Core API transmission failed. Verify backend server loops are active.")
except Exception as e:
    st.error(f"🔌 Connection Refused: Ensure FastAPI app layer is active on port 8000. Error: {e}")