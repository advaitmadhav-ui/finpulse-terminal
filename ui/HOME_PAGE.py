# ui/HOME_PAGE.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os
import sys
import yfinance as yf
import urllib.parse
import datetime
from streamlit_autorefresh import st_autorefresh

# Ensure the script can find the config file safely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_MAP

# 🔄 FAST LIVE REFRESH
st_autorefresh(interval=60000, limit=500, key="live_market_refresh")

# Initialize Session State for Routing
if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = None

# ==========================================
# 0. UI HELPERS & CSS
# ==========================================
def get_logo(asset_name):
    """Fetches the official corporate logo for the given asset using its primary web domain."""
    domains = {
        "HDFC Bank": "hdfcbank.com", "State Bank of India": "onlinesbi.sbi",
        "Trent": "westside.com", "DMart": "dmartindia.com",
        "Siemens India": "siemens.com", "ABB India": "abb.com",
        "Maruti Suzuki": "marutisuzuki.com", "Mahindra & Mahindra": "mahindra.com",
        "Microsoft": "microsoft.com", "NVIDIA": "nvidia.com"
    }
    domain = domains.get(asset_name, "google.com")
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

@st.cache_data(ttl=3600)
def fetch_live_exchange_rate():
    try:
        rate = yf.Ticker("INR=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except Exception:
        return 83.50 

def inject_custom_css():
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; }
        div[data-testid="stMetricDelta"] { font-size: 1rem !important; font-weight: 600 !important; }
        
        /* Card Hover Effects */
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            background-color: #111520 !important; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stVerticalBlock"] > div[style*="border"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.4);
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        
        /* Custom Accordion/Expander Styling */
        .streamlit-expanderHeader {
            font-size: 12px !important;
            color: gray !important;
            background-color: transparent !important;
            padding-top: 5px !important;
            padding-bottom: 5px !important;
        }
        .streamlit-expanderHeader:hover {
            color: #22ab59 !important;
        }
        div[data-testid="stExpander"] {
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }
        
        /* Dynamic Terminals Hyperlinks */
        .news-link {
            color: #ffffff !important;
            text-decoration: none !important;
            transition: color 0.15s ease-in-out !important;
        }
        .news-link:hover {
            color: #22ab59 !important;
            text-decoration: underline !important;
        }
        
        .stSelectbox div[data-baseweb="select"] {
            background-color: #111520 !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
        }
        div[data-testid="stButton"] > button { border-radius: 6px !important; }
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
        safe_ticker = urllib.parse.quote(ticker)
        API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{safe_ticker}"
        try:
            response = requests.get(API_ENDPOINT, timeout=2)
            if response.status_code == 200:
                payload = response.json()
                
                time_series = payload.get("time_series", [])
                fx_rate = fetch_live_exchange_rate() if ".NS" not in ticker else 1.0
                
                if time_series:
                    df = pd.DataFrame(time_series)
                    df['datetime'] = pd.to_datetime(df['datetime_str'])
                    df = df.sort_values('datetime')
                                         
                    latest_date = df['datetime'].dt.date.max()
                    today_df = df[df['datetime'].dt.date == latest_date]
                    prev_df = df[df['datetime'].dt.date < latest_date]
                    
                    raw_current = today_df['close'].iloc[-1] if not today_df.empty else df['close'].iloc[-1]
                    raw_prev = prev_df['close'].iloc[-1] if not prev_df.empty else raw_current
                    
                    current_price = raw_current * fx_rate
                    prev_close = raw_prev * fx_rate
                                         
                    pct_change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0.0
                    
                    display_df = df[df['datetime'].dt.date == latest_date].copy()
                    display_df['close'] = display_df['close'] * fx_rate
                    start_price = display_df['close'].iloc[0] if not display_df.empty else prev_close
                else:
                    current_price = 0.0
                    pct_change = 0.0
                    display_df = pd.DataFrame()
                    start_price = 0.0

                recent_news = payload.get("recent_news", [])
                avg_sentiment = pd.DataFrame(recent_news)['Sentiment'].astype(float).mean() if recent_news else 0.0

                summary_data.append({
                    "Asset": label,
                    "Ticker": ticker,
                    "Price": current_price,
                    "Change": pct_change,
                    "Sentiment": avg_sentiment,
                    "History_1D": display_df,
                    "Start_Price": start_price
                })
        except Exception:
            continue
    return summary_data

@st.cache_data(ttl=60)
def fetch_market_indices():
    try:
        nifty = yf.Ticker("^NSEI").history(period="1d", interval="15m")
        sensex = yf.Ticker("^BSESN").history(period="1d", interval="15m")
        if not nifty.empty and not sensex.empty:
            nifty['Pct'] = ((nifty['Close'] - nifty['Close'].iloc[0]) / nifty['Close'].iloc[0]) * 100
            sensex['Pct'] = ((sensex['Close'] - sensex['Close'].iloc[0]) / sensex['Close'].iloc[0]) * 100
            return nifty, sensex, nifty['Close'].iloc[-1], nifty['Pct'].iloc[-1], sensex['Close'].iloc[-1], sensex['Pct'].iloc[-1]
    except Exception:
        pass
    return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0

@st.cache_data(ttl=86400) 
def fetch_fundamental_data():
    metrics = []
    for label, ticker in TICKER_MAP.items():
        try:
            stock = yf.Ticker(urllib.parse.quote(ticker))
            info = stock.info
            eps = info.get('trailingEps') or 0
            pm = (info.get('profitMargins') or 0) * 100
            roe = (info.get('returnOnEquity') or 0) * 100
            roa = (info.get('returnOnAssets') or 0) * 100 
            pe = info.get('trailingPE') or 0

            metrics.append({
                "Asset": label,
                "Ticker": ticker,
                "EPS": eps, "PM (%)": pm, "ROE (%)": roe,
                "ROI (%)": roa, "P/E": pe
            })
        except Exception:
            continue
            
    if not metrics: return pd.DataFrame()
    df = pd.DataFrame(metrics)
    
    ranks = pd.DataFrame()
    ranks['EPS_R'] = df['EPS'].rank(ascending=True)
    ranks['PM_R'] = df['PM (%)'].rank(ascending=True)
    ranks['ROE_R'] = df['ROE (%)'].rank(ascending=True)
    ranks['ROI_R'] = df['ROI (%)'].rank(ascending=True)
    ranks['PE_R'] = df['P/E'].apply(lambda x: x if x > 0 else 9999).rank(ascending=False)

    max_possible_rank = len(df) * 5
    df['Overall Score'] = (ranks.sum(axis=1) / max_possible_rank) * 100
    return df.sort_values('Overall Score', ascending=False).reset_index(drop=True)

# ==========================================
# 2. UI COMPONENT GENERATORS
# ==========================================
def get_market_timing_badge(ticker):
    if ".NS" in ticker:
        market_name, hours, flag = "NSE / BSE (India)", "09:15 AM - 03:30 PM IST", "🇮🇳"
    else:
        market_name, hours, flag = "NASDAQ / NYSE (US)", "09:30 AM - 04:00 PM EST", "🇺🇸"
        
    return f"""
        <div style='display: inline-flex; align-items: center; background-color: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 4px 12px; border-radius: 15px; margin-bottom: 15px;'>
            <span style='font-size: 14px; margin-right: 6px;'>{flag}</span>
            <span style='color: #a0a0a0; font-size: 12px; font-weight: 500;'>{market_name} &bull; {hours}</span>
        </div>
    """

def create_mini_chart(df, color, start_price, ticker):
    """Creates a miniature version of the detailed 1D stock chart for the expander."""
    if df.empty: return go.Figure()
    
    y_min, y_max = df['close'].min(), df['close'].max()
    true_high, true_low = max(y_max, start_price), min(y_min, start_price)
    padding = (true_high - true_low) * 0.25
    if padding == 0: padding = start_price * 0.01
    
    fill_color = "rgba(34, 171, 89, 0.15)" if color == "#22ab59" else "rgba(234, 84, 85, 0.15)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['datetime'], y=df['close'], mode='lines', line=dict(color=color, width=2),
        fill='tozeroy', fillcolor=fill_color, hovertemplate="<b>₹%{y:.2f}</b><extra></extra>"
    ))
    
    fig.add_hline(y=start_price, line_dash="dot", line_color="gray", line_width=1, opacity=0.5)

    # ✅ FIX: Inherit boundaries directly from data to avoid Timezone Aware vs Naive mismatch bounds
    x_start = df['datetime'].min()
    x_end = df['datetime'].max()

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=120, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, range=[x_start, x_end]), 
        yaxis=dict(visible=False, range=[true_low - padding, true_high + padding]),
        showlegend=False, hovermode="x unified"
    )
    return fig

def render_overview_dashboard():
    summary_data = fetch_watchlist_summary()
    if not summary_data:
        st.info("Loading asset data pipelines. Please wait for the backend to sync...")
        return
             
    st.markdown("### Top Watchlist")
    cols = st.columns(5)
    for idx, data in enumerate(summary_data[:5]):
        with cols[idx]:
            with st.container(border=True):
                logo_html = f"<img src='{get_logo(data['Asset'])}' width='22' height='22' style='border-radius:50%; background:white; padding:2px; vertical-align:middle; margin-right:8px;'>"
                st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
                        <div style='font-weight: 600; font-size: 14px; display:flex; align-items:center;'>{logo_html}{data['Asset']}</div>
                        <span style='color: gray; font-size: 10px;'>{data['Ticker']}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                currency = "₹"
                color = "#22ab59" if data['Change'] >= 0 else "#ea5455"
                st.metric(label="", value=f"{currency} {data['Price']:,.2f}", delta=f"{data['Change']:+.2f}%", label_visibility="collapsed")
                
                if data['Sentiment'] > 0.05: badge = "<span style='color: #22ab59;'>●</span> <span style='color: gray; font-size: 12px;'>Bullish Bias</span>"
                elif data['Sentiment'] < -0.05: badge = "<span style='color: #ea5455;'>●</span> <span style='color: gray; font-size: 12px;'>Bearish Bias</span>"
                else: badge = "<span style='color: #7f7f7f;'>●</span> <span style='color: gray; font-size: 12px;'>Neutral Range</span>"
                st.markdown(badge, unsafe_allow_html=True)
                
                with st.expander("📊 View Chart", expanded=False):
                    if not data['History_1D'].empty:
                        st.plotly_chart(create_mini_chart(data['History_1D'], color, data['Start_Price'], data['Ticker']), use_container_width=True, config={'displayModeBar': False}, key=f"exp_chart_{data['Ticker']}")
                        if st.button("Full Dashboard →", key=f"btn_go_{data['Ticker']}", use_container_width=True, type="primary"):
                            st.session_state.selected_asset = data['Asset']
                            st.rerun()
                    else:
                        st.caption("Waiting for market data...")

    st.write("")
    
    st.markdown("### Market Overview")
    with st.container(border=True):
        nifty, sensex, n_val, n_pct, s_val, s_pct = fetch_market_indices()
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("NIFTY 50", f"{n_val:,.2f}", f"{n_pct:+.2f}%")
        with m2: st.metric("SENSEX", f"{s_val:,.2f}", f"{s_pct:+.2f}%")
        
        if not nifty.empty:
            macro_fig = go.Figure()
            macro_fig.add_trace(go.Scatter(x=nifty.index, y=nifty['Pct'], name="NIFTY 50", line=dict(color="#22ab59", width=2)))
            macro_fig.add_trace(go.Scatter(x=sensex.index, y=sensex['Pct'], name="SENSEX", line=dict(color="#1f77b4", width=2)))
            macro_fig.update_layout(
                margin=dict(l=0, r=40, t=10, b=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                xaxis=dict(showgrid=False, tickfont=dict(color="gray")), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", side="right", tickfont=dict(color="gray"), tickformat=".2f", ticksuffix="%")
            )
            st.plotly_chart(macro_fig, use_container_width=True, config={'displayModeBar': False}, key="macro_market_overview")
        else:
            st.info("Market is closed or macro data stream is initializing.")

    st.write("")

    st.markdown("### 🏛️ Fundamental Health Rankings")
    st.caption("Cross-asset evaluation using EPS, Profit Margin, ROE, ROI, and P/E. Click a row or bar to view detailed metrics.")
    
    with st.spinner("Compiling global fundamental data..."):
        fundamentals_df = fetch_fundamental_data()
        
    if not fundamentals_df.empty:
        fundamentals_df.insert(0, 'Logo', fundamentals_df['Asset'].apply(get_logo))
        tab1, tab2 = st.tabs(["🏆 Overall Score Leaderboard", "📋 Fundamental Matrix (Raw Data)"])
        
        with tab1:
            with st.container(border=True):
                fig = go.Figure(go.Bar(
                    x=fundamentals_df['Overall Score'],
                    y=fundamentals_df['Asset'],
                    orientation='h',
                    marker=dict(color=fundamentals_df['Overall Score'], colorscale='Viridis'),
                    text=fundamentals_df['Overall Score'].apply(lambda x: f"{x:.1f}/100"),
                    textposition='auto',
                    hovertemplate="<b>%{y}</b><br>Overall Health Score: %{x:.2f}<extra></extra>"
                ))
                fig.update_layout(
                    margin=dict(l=10, r=40, t=10, b=20), height=450, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(title="Algorithmic Health Score", gridcolor="rgba(128,128,128,0.1)", range=[0, 100]),
                    yaxis=dict(autorange="reversed", tickfont=dict(color="gray", size=13))
                )
                
                chart_event = st.plotly_chart(
                    fig, 
                    use_container_width=True, 
                    config={'displayModeBar': False}, 
                    on_select="rerun", 
                    selection_mode="points", 
                    key="health_rankings_chart"
                )
                
                if chart_event and len(chart_event.selection.get("points", [])) > 0:
                    selected_asset = chart_event.selection["points"][0].get("y")
                    if selected_asset in TICKER_MAP:
                        st.session_state.selected_asset = selected_asset
                        st.rerun()
                
        with tab2:
            with st.container(border=True):
                display_df = fundamentals_df.drop(columns=['Ticker'])
                
                table_event = st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="health_rankings_table",
                    column_config={
                        "Logo": st.column_config.ImageColumn("", width="small"),
                        "Asset": st.column_config.TextColumn("Company"),
                        "Overall Score": st.column_config.ProgressColumn("Overall Score", format="%.1f", min_value=0, max_value=100),
                        "EPS": st.column_config.NumberColumn("EPS", format="%.2f"),
                        "PM (%)": st.column_config.NumberColumn("Profit Margin", format="%.1f%%"),
                        "ROE (%)": st.column_config.NumberColumn("ROE", format="%.1f%%"),
                        "ROI (%)": st.column_config.NumberColumn("ROI (Assets)", format="%.1f%%"),
                        "P/E": st.column_config.NumberColumn("P/E Ratio", format="%.2f"),
                    }
                )
                
                if table_event and len(table_event.selection.get("rows", [])) > 0:
                    selected_row_idx = table_event.selection["rows"][0]
                    selected_asset = display_df.iloc[selected_row_idx]['Asset']
                    if selected_asset in TICKER_MAP:
                        st.session_state.selected_asset = selected_asset
                        st.rerun()
    else:
        st.warning("Fundamental data currently unavailable. Waiting for Yahoo Finance to respond.")

# ==========================================
# 3. INDIVIDUAL ASSET DASHBOARD LOGIC
# ==========================================
def render_dynamic_stock_chart(time_series_data, ticker_name):
    metric_col1, metric_col2, metric_col3, spacer, pill_col = st.columns([1.9, 1.9, 2.2, 0.2, 2.5])
    with pill_col:
        selected_period = st.pills("Timeframe", options=["1D", "1W", "1M", "2M", "1Y"], default="1D", label_visibility="collapsed")
        
    fx_rate = fetch_live_exchange_rate() if ".NS" not in ticker_name else 1.0
    x_axis_range = None
        
    if selected_period == "1Y":
        with st.spinner("Fetching historical year data..."):
            try:
                raw_yf = yf.Ticker(urllib.parse.quote(ticker_name)).history(period="1y", interval="1d")
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
            
            # ✅ FIX: Extract boundaries directly from the data series to automatically match Timezone-Aware formats
            x_start = df_filtered['datetime'].min()
            x_end = df_filtered['datetime'].max()
            x_axis_range = [x_start, x_end]
            
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
        
    df_filtered = df_filtered.copy()
    start_price = start_price * fx_rate
    df_filtered['close'] = df_filtered['close'] * fx_rate
    df_filtered['high'] = df_filtered['high'] * fx_rate
    df_filtered['low'] = df_filtered['low'] * fx_rate
        
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

    currency = "₹"
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

    if ".NS" in ticker_name:
        closed_hours = [15.5, 9.25]
    else:
        closed_hours = [16.0, 9.5]
    hourly_break = dict(bounds=closed_hours, pattern="hour") if selected_period == "1W" else dict(values=[])
    
    fig.update_layout(
        margin=dict(l=10, r=50, t=10, b=30), height=400, hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=True, tickfont=dict(color="gray", size=10), showline=False, 
            showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dot", spikecolor="#b3b3b3", spikethickness=1.5, 
            rangebreaks=[dict(bounds=["sat", "mon"]), hourly_break],
            range=x_axis_range, 
            autorange=False if x_axis_range else True
        ),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False, showticklabels=True, tickfont=dict(color="gray", size=10), tickformat=",.0f", side="right", showline=False, autorange=False, range=[y_min, y_max])
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"detailed_chart_{ticker_name}_{selected_period}")

# ==========================================
# 4. MAIN PAGE ROUTING
# ==========================================
st.markdown("## Market Overview")
st.markdown("<span style='color: gray; font-size: 14px;'>Track top assets, analyze macro trends, and uncover market opportunities.</span>", unsafe_allow_html=True)
st.write("")

if not st.session_state.selected_asset:
    render_overview_dashboard()
else:
    if st.button("⬅ Back to Market Overview", type="secondary"):
        st.session_state.selected_asset = None
        st.rerun()
    
    st.write("---")
    
    selected_label = st.session_state.selected_asset
    target_ticker = TICKER_MAP[selected_label]
    
    safe_ticker = urllib.parse.quote(target_ticker)
    API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{safe_ticker}"

    try:
        response = requests.get(API_ENDPOINT)
        if response.status_code == 200:
            payload = response.json()
            time_series = payload.get("time_series", [])
            recent_news = payload.get("recent_news", [])
            
            logo_html = f"<img src='{get_logo(selected_label)}' width='28' height='28' style='border-radius:50%; background:white; padding:2px; vertical-align:middle; margin-right:10px; margin-top:-4px;'>"
            st.markdown(f"### {logo_html}{selected_label} Dashboard", unsafe_allow_html=True)
            st.markdown(get_market_timing_badge(target_ticker), unsafe_allow_html=True)
            
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
                            
                            source_url = "#"
                            for key in ["url", "URL", "Url", "link", "Link"]:
                                val = item.get(key)
                                if val and str(val).strip() != "":
                                    source_url = str(val).strip()
                                    break
                                                     
                            if score > 0.05: sentiment_tag = f"<span style='color: #22ab59;'>🟢 Bullish (+{score:.2f})</span>"
                            elif score < -0.05: sentiment_tag = f"<span style='color: #ea5455;'>🔴 Bearish ({score:.2f})</span>"
                            else: sentiment_tag = "<span style='color: gray;'>⚪ Neutral (0.00)</span>"
                                                         
                            with st.container(border=True):
                                st.caption(f"📅 {timestamp} | {item.get('Source', 'News Feed')}")
                                st.markdown(f"<div style='margin-bottom:6px;'><a class='news-link' href='{source_url}' target='_blank'><b>{headline} ↗</b></a></div>", unsafe_allow_html=True)
                                st.markdown(f"{sentiment_tag}", unsafe_allow_html=True)
                else:
                    st.info("No evaluated news metrics match this tracking signature currently.")
        else:
            st.error(f"🚨 Core API transmission failed. Verify backend server loops are active.")
    except Exception as e:
        st.error(f"❌ Connection Refused: Ensure FastAPI app layer is active on port 8000. Error: {e}")