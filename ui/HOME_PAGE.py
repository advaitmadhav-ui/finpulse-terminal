# ui/home.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os
import sys
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# Ensure the script can find the config file safely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_MAP

# Silently refresh the UI every 60 seconds to act as a live terminal
st_autorefresh(interval=60000, limit=500, key="live_market_refresh")

# Initialize Session State for Routing
if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = None

# ==========================================
# 0. CUSTOM CSS THEMING
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        /* Base Theme Adjustments */
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
        /* Metric Card Styling */
        div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; }
        div[data-testid="stMetricDelta"] { font-size: 1rem !important; font-weight: 600 !important; }
        
        /* Smooth Borders and Backgrounds */
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            background-color: #111520 !important; /* Darker card background */
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        
        /* Selectbox styling */
        .stSelectbox div[data-baseweb="select"] {
            background-color: #111520 !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
        }
        
        /* Make inline buttons sleeker */
        div[data-testid="stButton"] > button {
            border-radius: 6px !important;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
# 1. MACRO OVERVIEW DATA PIPELINES
# ==========================================
@st.cache_data(ttl=60)
def fetch_watchlist_summary():
    summary_data = []
    for label, ticker in TICKER_MAP.items():
        API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{ticker}"
        try:
            response = requests.get(API_ENDPOINT, timeout=2)
            if response.status_code == 200:
                payload = response.json()
                
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
                    spark_df = df.tail(20)
                else:
                    current_price = 0.0
                    pct_change = 0.0
                    spark_df = pd.DataFrame()

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
                    "Sentiment": avg_sentiment,
                    "History": spark_df
                })
        except Exception:
            continue
    return summary_data

@st.cache_data(ttl=300)
def fetch_market_indices():
    try:
        nifty = yf.Ticker("^NSEI").history(period="1d", interval="15m")
        sensex = yf.Ticker("^BSESN").history(period="1d", interval="15m")
        if not nifty.empty and not sensex.empty:
            nifty['Pct'] = ((nifty['Close'] - nifty['Close'].iloc[0]) / nifty['Close'].iloc[0]) * 100
            sensex['Pct'] = ((sensex['Close'] - sensex['Close'].iloc[0]) / sensex['Close'].iloc[0]) * 100
            nifty_latest = nifty['Close'].iloc[-1]
            nifty_change = nifty['Pct'].iloc[-1]
            sensex_latest = sensex['Close'].iloc[-1]
            sensex_change = sensex['Pct'].iloc[-1]
            return nifty, sensex, nifty_latest, nifty_change, sensex_latest, sensex_change
    except Exception:
        pass
    return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0

@st.cache_data(ttl=3600) 
def fetch_macro_leaderboard(timeframe):
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

# ==========================================
# 2. UI COMPONENT GENERATORS
# ==========================================
def create_sparkline(df, color):
    if df.empty: return go.Figure()
    fig = go.Figure(go.Scatter(x=df['datetime'], y=df['close'], mode='lines', line=dict(color=color, width=2.5)))
    fig.update_layout(
        margin=dict(l=0, r=0, t=5, b=5),
        height=60,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False, hovermode=False
    )
    return fig

def create_sentiment_gauge(score):
    normalized_val = ((score + 1) / 2) * 100
    if score > 0.05: color, label = "#22ab59", "Bullish"
    elif score < -0.05: color, label = "#ea5455", "Bearish"
    else: color, label = "#7f7f7f", "Neutral"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=normalized_val,
        number={'font': {'size': 40, 'color': 'white'}, 'suffix': "", 'valueformat': ".0f"},
        title={'text': f"<span style='font-size: 16px; color:{color};'>{label}</span>", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [0, 100], 'visible': False},
            'bar': {'color': color, 'thickness': 0.8},
            'bgcolor': "rgba(255,255,255,0.05)",
            'shape': "angular"
        }
    ))
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=10),
        height=220,
        paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}
    )
    return fig

def render_overview_dashboard():
    summary_data = fetch_watchlist_summary()
    if not summary_data:
        st.info("Loading asset data pipelines. Please wait for the backend to sync...")
        return
             
    # --- 1. TOP WATCHLIST CAROUSEL ---
    st.markdown("### Top Watchlist")
    cols = st.columns(5)
    for idx, data in enumerate(summary_data[:5]):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
                        <span style='font-weight: 600; font-size: 14px;'>{data['Asset']}</span>
                        <span style='color: gray; font-size: 10px;'>{data['Ticker']}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                currency = "$" if ".NS" not in data['Ticker'] else "₹"
                color = "#22ab59" if data['Change'] >= 0 else "#ea5455"
                st.metric(label="", value=f"{currency} {data['Price']:,.2f}", delta=f"{data['Change']:+.2f}%", label_visibility="collapsed")
                st.plotly_chart(create_sparkline(data['History'], color), use_container_width=True, config={'displayModeBar': False})
                
                if data['Sentiment'] > 0.05: badge = "<span style='color: #22ab59;'>●</span> <span style='color: gray; font-size: 12px;'>Bullish Bias</span>"
                elif data['Sentiment'] < -0.05: badge = "<span style='color: #ea5455;'>●</span> <span style='color: gray; font-size: 12px;'>Bearish Bias</span>"
                else: badge = "<span style='color: #7f7f7f;'>●</span> <span style='color: gray; font-size: 12px;'>Neutral Range</span>"
                st.markdown(badge, unsafe_allow_html=True)
                
                # Interactive Routing Button
                if st.button("📊 View", key=f"btn_top_{data['Ticker']}", use_container_width=True):
                    st.session_state.selected_asset = data['Asset']
                    st.rerun()

    st.write("")
    
    # --- 2. MIDDLE SECTION: MARKET OVERVIEW & SENTIMENT ---
    mid_col1, mid_col2 = st.columns([2.2, 1])
    with mid_col1:
        st.markdown("### Market Overview")
        with st.container(border=True):
            nifty, sensex, n_val, n_pct, s_val, s_pct = fetch_market_indices()
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("NIFTY 50", f"{n_val:,.2f}", f"{n_pct:+.2f}%")
            with m2: st.metric("SENSEX", f"{s_val:,.2f}", f"{s_pct:+.2f}%")
            
            if not nifty.empty:
                macro_fig = go.Figure()
                macro_fig.add_trace(go.Scatter(x=nifty.index, y=nifty['Pct'], name="NIFTY 50", line=dict(color="#22ab59", width=2)))
                macro_fig.add_trace(go.Scatter(x=sensex.index, y=sensex['Pct'], name="SENSEX", line=dict(color="#1f77b4", width=2)))
                macro_fig.update_layout(
                    margin=dict(l=0, r=40, t=10, b=10), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    xaxis=dict(showgrid=False, tickfont=dict(color="gray")), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", side="right", tickfont=dict(color="gray"), tickformat=".2f", ticksuffix="%")
                )
                st.plotly_chart(macro_fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("Market is closed or macro data stream is initializing.")

    with mid_col2:
        st.markdown("### Market Sentiment")
        with st.container(border=True):
            global_sent = sum(d['Sentiment'] for d in summary_data) / len(summary_data)
            advancing = sum(1 for d in summary_data if d['Change'] > 0)
            declining = sum(1 for d in summary_data if d['Change'] < 0)
            unchanged = len(summary_data) - advancing - declining
            
            st.plotly_chart(create_sentiment_gauge(global_sent), use_container_width=True, config={'displayModeBar': False})
            s1, s2, s3 = st.columns(3)
            with s1:
                st.markdown("<div style='text-align: center; color: gray; font-size: 11px;'>Advancing</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; color: #22ab59; font-weight: bold;'>{advancing}</div>", unsafe_allow_html=True)
            with s2:
                st.markdown("<div style='text-align: center; color: gray; font-size: 11px;'>Declining</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; color: #ea5455; font-weight: bold;'>{declining}</div>", unsafe_allow_html=True)
            with s3:
                st.markdown("<div style='text-align: center; color: gray; font-size: 11px;'>Unchanged</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; color: gray; font-weight: bold;'>{unchanged}</div>", unsafe_allow_html=True)
            st.write("")
    st.write("")

    # --- 3. PERFORMANCE LEADERBOARD LIST ---
    lead_title_col, lead_toggle_col = st.columns([4, 1])
    with lead_title_col:
        st.markdown("### 🏆 Macro Returns Leaderboard")
        st.caption("Ranked absolute performance of watchlisted assets across historical macro windows.")
    with lead_toggle_col:
        selected_horizon = st.pills("Timeframe", options=["6M", "1Y", "3Y"], default="1Y", label_visibility="collapsed", key="macro_leaderboard_toggle")
             
    with st.spinner(f"Computing historical returns for window: {selected_horizon}..."):
        leaderboard_list = fetch_macro_leaderboard(selected_horizon)
             
    if not leaderboard_list:
        st.warning("Historical data parsing engines are initializing.")
        return
         
    with st.container(border=True):
        # Header Row
        st.markdown("""
            <div style='display: flex; padding: 10px 15px; border-bottom: 1px solid rgba(255,255,255,0.1); font-weight: 600; font-size: 11px; color: gray; text-transform: uppercase;'>
                <div style='flex: 0.5;'>Rank</div>
                <div style='flex: 2;'>Asset Identifier</div>
                <div style='flex: 1.5; text-align: right;'>Last Close</div>
                <div style='flex: 1.5; text-align: right;'>Accumulated Returns</div>
                <div style='flex: 0.8; text-align: right;'>Action</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Interactive Rows via Streamlit Columns
        for rank, item in enumerate(leaderboard_list, start=1):
            if item['Return'] >= 0: color_style, arrow = "color: #22ab59;", "▲"
            else: color_style, arrow = "color: #ea5455;", "▼"
            currency = "$" if ".NS" not in item['Ticker'] else "₹"
                         
            c1, c2, c3, c4, c5 = st.columns([0.5, 2, 1.5, 1.5, 0.8])
            with c1: st.markdown(f"<div style='margin-top: 10px; color: gray; font-size: 14px;'>#{rank}</div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div style='margin-top: 10px; font-weight: 500; font-size: 14px;'>{item['Asset']} <span style='font-size: 10px; color: gray; margin-left: 8px;'>{item['Ticker']}</span></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div style='margin-top: 10px; text-align: right; font-size: 14px;'>{currency} {item['Current']:,.2f}</div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div style='margin-top: 10px; text-align: right; {color_style} font-weight: 600; font-size: 14px;'>{arrow} {abs(item['Return']):.2f}%</div>", unsafe_allow_html=True)
            with c5:
                # Interactive Routing Button
                if st.button("Inspect", key=f"btn_lead_{item['Ticker']}", use_container_width=True):
                    st.session_state.selected_asset = item['Asset']
                    st.rerun()
            st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

# ==========================================
# 3. INDIVIDUAL ASSET DASHBOARD LOGIC
# ==========================================
def render_dynamic_stock_chart(time_series_data, ticker_name):
    metric_col1, metric_col2, metric_col3, spacer, pill_col = st.columns([1.9, 1.9, 2.2, 0.2, 2.5])
    with pill_col:
        selected_period = st.pills("Timeframe", options=["1D", "1W", "1M", "2M", "1Y"], default="1D", label_visibility="collapsed")
        
    if selected_period == "1Y":
        with st.spinner("Fetching historical year data..."):
            try:
                raw_yf = yf.Ticker(ticker_name).history(period="1y", interval="1d")
                if raw_yf.empty:
                    st.error("Could not retrieve historical 1Y data from Yahoo Finance.")
                    return
                df_filtered = raw_yf.reset_index().rename(columns={'Date': 'datetime', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'})
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
            start_price = previous_days_df['close'].iloc[-1] if not previous_days_df.empty else df_filtered['close'].iloc[0]
        elif selected_period == "1W":
            df_filtered = df.tail(125).copy()
            start_price = df_filtered['close'].iloc[0]
        elif selected_period == "1M":
            latest_date = df['datetime'].dt.date.max()
            start_date = latest_date - pd.Timedelta(days=30)
            df_raw = df[df['datetime'].dt.date >= start_date].copy()
            df_raw['date_group'] = df_raw['datetime'].dt.date
            df_filtered = df_raw.groupby('date_group').agg({'datetime': 'last', 'high': 'max', 'low': 'min', 'close': 'last'}).reset_index()
            start_price = df_filtered['close'].iloc[0]
        elif selected_period == "2M": 
            df_raw = df.copy()
            df_raw['date_group'] = df_raw['datetime'].dt.date
            df_filtered = df_raw.groupby('date_group').agg({'datetime': 'last', 'high': 'max', 'low': 'min', 'close': 'last'}).reset_index()
            start_price = df_filtered['close'].iloc[0]

    if df_filtered.empty:
        st.info("Insufficient data points captured for this specific timeframe.")
        return
        
    period_high, period_low, end_price = df_filtered['high'].max(), df_filtered['low'].min(), df_filtered['close'].iloc[-1]
    true_high, true_low = max(period_high, start_price), min(period_low, start_price)
    spread = true_high - true_low
    spread = true_high * 0.01 if spread == 0 else spread
    padding = spread * 0.25
    y_min, y_max = true_low - padding, true_high + padding
         
    price_delta = end_price - start_price
    pct_change = (price_delta / start_price) * 100 if start_price != 0 else 0.0
    if price_delta >= 0: line_color, fill_color, arrow = "#22ab59", "rgba(34, 171, 89, 0.15)", "▲"
    else: line_color, fill_color, arrow = "#ea5455", "rgba(234, 84, 85, 0.15)", "▼"

    currency = "$" if ".NS" not in ticker_name else "₹"
    with metric_col1: st.metric("High", f"{currency} {period_high:,.2f}")
    with metric_col2: st.metric("Low", f"{currency} {period_low:,.2f}")
    with metric_col3: st.metric("Returns", f"{arrow} {abs(pct_change):.2f}%", delta=f"{price_delta:+.2f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_filtered['datetime'], y=df_filtered['close'], mode='lines', line=dict(color=line_color, width=2),
        fill='tozeroy', fillcolor=fill_color, hovertemplate=f"<b>{currency} %{{y:.2f}}</b><br><span style='color:gray; font-size:12px;'>%{{x|%b %d, %Y %I:%M %p}}</span><extra></extra>"
    ))
    if selected_period == "1D":
        fig.add_hline(y=start_price, line_dash="dot", line_color="gray", line_width=1.5, opacity=0.6, annotation_text="Prev. Close", annotation_position="bottom right", annotation_font_size=10, annotation_font_color="gray")
        
    fig.update_layout(
        margin=dict(l=10, r=50, t=10, b=30), height=400, hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=True, tickfont=dict(color="gray", size=10), showline=False, showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dot", spikecolor="#b3b3b3", spikethickness=1.5, rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour") if selected_period in ["1D", "1W"] else dict(values=[])]),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False, showticklabels=True, tickfont=dict(color="gray", size=10), tickformat=",.0f", side="right", showline=False, autorange=False, range=[y_min, y_max])
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 4. MAIN PAGE ROUTING
# ==========================================
st.markdown("## Market Overview")
st.markdown("<span style='color: gray; font-size: 14px;'>Track top assets, analyze macro trends, and uncover market opportunities.</span>", unsafe_allow_html=True)
st.write("")

# Dynamic State Router
if not st.session_state.selected_asset:
    render_overview_dashboard()
else:
    # Render Back Button to exit individual view
    if st.button("⬅ Back to Market Overview", type="secondary"):
        st.session_state.selected_asset = None
        st.rerun()
    
    st.write("---")
    
    selected_label = st.session_state.selected_asset
    target_ticker = TICKER_MAP[selected_label]
    API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{target_ticker}"

    try:
        response = requests.get(API_ENDPOINT)
        if response.status_code == 200:
            payload = response.json()
            time_series = payload.get("time_series", [])
            recent_news = payload.get("recent_news", [])
            
            st.markdown(f"### {selected_label} Dashboard")
            col1, col2 = st.columns([2.5, 1])
                     
            with col1:
                render_dynamic_stock_chart(time_series, target_ticker)
                             
            with col2:
                st.subheader("Live Asset Sentiment")
                if recent_news:
                    with st.container(height=450):
                        for item in recent_news:
                            score = float(item["Sentiment"])
                            headline = item["Headline"]
                            timestamp = item["Event_Time"].replace("T", " ").replace("Z", "")
                                                     
                            if score > 0.05: sentiment_tag = f"<span style='color: #22ab59;'>🟢 Bullish (+{score:.2f})</span>"
                            elif score < -0.05: sentiment_tag = f"<span style='color: #ea5455;'>🔴 Bearish ({score:.2f})</span>"
                            else: sentiment_tag = "<span style='color: gray;'>⚪ Neutral (0.00)</span>"
                                                         
                            with st.container(border=True):
                                st.caption(f"📅 {timestamp} | {item.get('Source', 'News Feed')}")
                                st.markdown(f"**{headline}**")
                                st.markdown(f"{sentiment_tag}", unsafe_allow_html=True)
                else:
                    st.info("No evaluated news metrics match this tracking signature currently.")
        else:
            st.error(f"🚨 Core API transmission failed. Verify backend server loops are active.")
    except Exception as e:
        st.error(f"❌ Connection Refused: Ensure FastAPI app layer is active on port 8000. Error: {e}")