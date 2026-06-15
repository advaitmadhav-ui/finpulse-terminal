# ui/pages/Compare_Stocks.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
import os
import sys
import urllib.parse
import datetime

# System path expansion to link to config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import TICKER_MAP

def get_logo(asset_name):
    domains = {
        "HDFC Bank": "hdfcbank.com", "State Bank of India": "onlinesbi.sbi",
        "Trent": "westside.com", "DMart": "dmartindia.com",
        "Siemens India": "siemens.com", "ABB India": "abb.com",
        "Maruti Suzuki": "marutisuzuki.com", "Mahindra & Mahindra": "mahindra.com",
        "Microsoft": "microsoft.com", "NVIDIA": "nvidia.com"
    }
    domain = domains.get(asset_name, "google.com")
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

# ==========================================
# 0. CUSTOM CSS THEMING
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
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
        
        .stSelectbox div[data-baseweb="select"] {
            background-color: #111520 !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
# 1. PAGE HEADER & DICTIONARIES
# ==========================================
st.markdown("## 📊 Sector & Trend Comparison")
st.markdown("<span style='color: gray; font-size: 14px;'>Compare normalized price trends and view real-time AI sentiment analysis across specific market sectors.</span>", unsafe_allow_html=True)
st.write("")

COMPANY_INFO = {
    "HDFC Bank": "India's largest private sector bank by assets, providing a wide range of retail banking, wholesale banking, and treasury operations.",
    "State Bank of India": "An Indian multinational, public sector banking and financial services statutory body. It is the largest bank in India.",
    "Trent": "A retail arm of the Tata Group, operating popular clothing, footwear, and apparel chains like Westside, Zudio, and Misbu.",
    "DMart": "An Indian chain of hypermarkets founded by Radhakishan Damani, operated and managed by Avenue Supermarts Limited.",
    "Siemens India": "The Indian arm of the German engineering giant, focusing on industrial automation, infrastructure, transport, and electrical transmission.",
    "ABB India": "A leading global technology company that specializes in electrification, robotics, automation, and advanced power grids.",
    "Maruti Suzuki": "India's leading passenger automobile manufacturer, operating as a major subsidiary of Japanese automaker Suzuki Motor Corporation.",
    "Mahindra & Mahindra": "An Indian multinational automotive manufacturing corporation, globally recognized for its rugged SUVs, commercial vehicles, and tractors.",
    "Microsoft": "A global technology giant known for enterprise software, operating systems, cloud computing (Azure), hardware, and computational AI solutions.",
    "NVIDIA": "A pioneer of GPU-accelerated hardware architectures, specializing in high-performance graphics chips, supercomputing, and enterprise AI tech."
}

SECTOR_MAP = {
    "Banking": ["HDFC Bank", "State Bank of India"],
    "Retail": ["Trent", "DMart"],
    "Manufacturing": ["Siemens India", "ABB India"],
    "Automobile": ["Maruti Suzuki", "Mahindra & Mahindra"],
    "Global Tech": ["Microsoft", "NVIDIA"]
}

# ==========================================
# 2. CONTROLS
# ==========================================
col_sel1, col_sel2 = st.columns([2.5, 1.5])
with col_sel1:
    selected_sector = st.selectbox(
        "Select Market Sector:", 
        options=list(SECTOR_MAP.keys()),
        index=0,
        label_visibility="collapsed"
    )
with col_sel2:
    selected_period = st.pills("Timeframe", options=["1D", "1W", "1M", "2M"], default="1M", label_visibility="collapsed")

st.write("---")

# ==========================================
# 3. SELF-HEALING DATA FETCHING LOGIC
# ==========================================
selected_names = SECTOR_MAP[selected_sector]

all_data = []
api_responses = {} 
score_cards = {}
         
with st.spinner(f"Analyzing and ranking the {selected_sector} sector..."):
    for name in selected_names:
        ticker = TICKER_MAP[name]
        safe_ticker = urllib.parse.quote(ticker)
        
        # --- A. FETCH FUNDAMENTALS VIA YFINANCE ---
        fundamental_score = 0
        try:
            stock = yf.Ticker(safe_ticker)
            info = stock.info
            eps = info.get('trailingEps') or 0
            pm = (info.get('profitMargins') or 0) * 100
            roe = (info.get('returnOnEquity') or 0) * 100
            roa = (info.get('returnOnAssets') or 0) * 100 
            pe = info.get('trailingPE') or 0
            
            # Score assignment out of 100 max (5 criteria * 20 points)
            if eps > 0: fundamental_score += 20
            if pm > 10: fundamental_score += 20
            if roe > 15: fundamental_score += 20
            if roa > 10: fundamental_score += 20
            if 0 < pe < 40: fundamental_score += 20
        except Exception:
            fundamental_score = 50  # Balanced fallback score if yfinance times out
            
        # --- B. FETCH PRICES AND NEWS VIA BACKEND ---
        time_series = []
        try:
            response = requests.get(f"http://127.0.0.1:8000/api/data/{safe_ticker}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                api_responses[name] = data 
                time_series = data.get("time_series", [])
                news = data.get("recent_news", [])
                
                # --- C. CALCULATE SENTIMENT SCORE ---
                pos, neg, neu = 0, 0, 0
                for article in news:
                    score = article.get("Sentiment")
                    if score is not None:
                        score = float(score)
                        if score > 0.05: pos += 1
                        elif score < -0.05: neg += 1
                        else: neu += 1
                
                total_articles = pos + neg + neu
                sentiment_score = (pos / total_articles) * 100 if total_articles > 0 else 50
                
                # --- D. COMPILE WEIGHTED OVERALL SCORE ---
                combined_score = (fundamental_score + sentiment_score) / 2
                score_cards[name] = {
                    "fundamental": fundamental_score,
                    "sentiment": sentiment_score,
                    "overall": combined_score
                }
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend API. Ensure Uvicorn is running.")
            break
        except Exception:
            pass # Fails gracefully so fallback can trigger
            
        # --- E. BULLETPROOF TIME SERIES PARSING ---
        df = pd.DataFrame()
        
        # Step 1: Try to parse the database API time_series
        if time_series:
            temp_df = pd.DataFrame(time_series)
            price_col = next((col for col in temp_df.columns if col.lower() == 'close'), None)
            date_col = next((col for col in temp_df.columns if col.lower() in ['datetime_str', 'timestamp', 'datetime']), None)
            if price_col and date_col:
                # Strip timezone so Plotly rangebreaks evaluate the exact local hour
                df['Datetime'] = pd.to_datetime(temp_df[date_col], errors='coerce').dt.tz_localize(None)
                df['Price'] = pd.to_numeric(temp_df[price_col], errors='coerce')
                
        # Step 2: SELF HEALING FALLBACK (If DB is empty, fetch live from Yahoo!)
        if df.empty:
            try:
                yf_period = "1d" if selected_period == "1D" else "3mo"
                yf_interval = "5m" if selected_period == "1D" else "1d"
                hist = yf.Ticker(ticker).history(period=yf_period, interval=yf_interval)
                if not hist.empty:
                    hist = hist.reset_index()
                    d_col = 'Datetime' if 'Datetime' in hist.columns else 'Date'
                    df['Datetime'] = pd.to_datetime(hist[d_col], errors='coerce').dt.tz_localize(None)
                    df['Price'] = pd.to_numeric(hist['Close'], errors='coerce')
            except Exception:
                pass

        # Step 3: Filter and Normalize
        if not df.empty:
            df['Stock'] = name
            df = df.dropna(subset=['Datetime', 'Price'])
            df = df.sort_values('Datetime')
            
            if selected_period == "1D":
                latest_date = df['Datetime'].dt.date.max()
                df = df[df['Datetime'].dt.date == latest_date]
            elif selected_period == "1W":
                latest_date = df['Datetime'].dt.date.max()
                start_date = latest_date - pd.Timedelta(days=7)
                df = df[df['Datetime'].dt.date >= start_date]
            elif selected_period == "1M":
                latest_date = df['Datetime'].dt.date.max()
                start_date = latest_date - pd.Timedelta(days=30)
                df = df[df['Datetime'].dt.date >= start_date]
            elif selected_period == "2M":
                latest_date = df['Datetime'].dt.date.max()
                start_date = latest_date - pd.Timedelta(days=60)
                df = df[df['Datetime'].dt.date >= start_date]
            
            if not df.empty:
                start_price = df['Price'].iloc[0]
                df['Normalized_Price'] = (df['Price'] / start_price) * 100 if start_price != 0 else 100
                all_data.append(df[['Datetime', 'Price', 'Normalized_Price', 'Stock']])

# ==========================================
# 4. WINNER ANNOUNCEMENT SHOWDOWN BANNER
# ==========================================
if score_cards:
    winner_name = max(score_cards, key=lambda k: score_cards[k]['overall'])
    winner_stats = score_cards[winner_name]
    
    st.markdown("### 🏆 Sector Showdown Winner")
    with st.container(border=True):
        w_col1, w_col2, w_col3 = st.columns([1.2, 1, 1])
        
        with w_col1:
            logo_html = f"<img src='{get_logo(winner_name)}' width='32' height='32' style='border-radius:50%; background:white; padding:2px; vertical-align:middle; margin-right:12px;'>"
            st.markdown(f"<div style='margin-top:10px;'>{logo_html}<span style='font-size:22px; font-weight:bold; color:#22ab59;'>{winner_name}</span></div>", unsafe_allow_html=True)
            st.markdown("<span style='font-size:12px; color:gray; margin-left:48px;'>Outperforming peer matrices within the sector</span>", unsafe_allow_html=True)
            
        with w_col2:
            st.metric(label="Overall Combined Score", value=f"{winner_stats['overall']:.1f}%")
            
        with w_col3:
            st.markdown(f"""
                <div style='font-size:12px; color:gray; margin-top:5px;'>
                    <div>🧬 Fundamental Health: <b>{winner_stats['fundamental']:.0f}%</b></div>
                    <div style='margin-top:4px;'>🧠 Live Sentiment Index: <b>{winner_stats['sentiment']:.0f}%</b></div>
                </div>
            """, unsafe_allow_html=True)
    st.write("")

# ==========================================
# 5. PRICE CHART SECTION (NORMALIZED)
# ==========================================
if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    # Ensure timezone naive for accurate plot rendering
    combined_df['Datetime'] = pd.to_datetime(combined_df['Datetime']).dt.tz_localize(None)
    combined_df['Price'] = pd.to_numeric(combined_df['Price'], errors='coerce')
    combined_df['Stock'] = combined_df['Stock'].astype(str)
    combined_df = combined_df.dropna(subset=['Datetime', 'Price', 'Stock'])
             
    if not combined_df.empty:
        st.markdown(f"### 📈 {selected_sector} Relative Performance ({selected_period})")
        with st.container(border=True):
            fig = go.Figure()
            unique_stocks = combined_df['Stock'].unique()
                         
            for stock_name in unique_stocks:
                stock_data = combined_df[combined_df['Stock'] == stock_name].sort_values('Datetime')
                fig.add_trace(go.Scatter(
                    x=stock_data['Datetime'], 
                    y=stock_data['Normalized_Price'], 
                    mode='lines', 
                    name=stock_name,
                    line=dict(width=2),
                    hovertemplate="<b>%{data.name}</b><br>Relative Growth: %{y:.2f}%<extra></extra>"
                ))
            
            # --- DYNAMIC MARKET HOURS LOGIC ---
            sample_ticker = TICKER_MAP[selected_names[0]]
            if ".NS" in sample_ticker:
                closed_hours = [15.5, 9.25]  
            else:
                closed_hours = [20.0, 4.0]   
            
            # Build safe rangebreaks array
            r_breaks = [dict(bounds=["sat", "mon"])]
            if selected_period in ["1D", "1W"]:
                r_breaks.append(dict(bounds=closed_hours, pattern="hour"))
                         
            fig.update_layout(
                margin=dict(l=10, r=20, t=20, b=20),
                height=450,
                hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    showgrid=False, 
                    tickfont=dict(color="gray", size=10),
                    rangebreaks=r_breaks 
                ),
                yaxis=dict(
                    titlefont=dict(color="gray", size=11),
                    showgrid=True, 
                    gridcolor="rgba(255, 255, 255, 0.05)",
                    tickfont=dict(color="gray", size=10),
                    zeroline=True,
                    zerolinecolor="rgba(255, 255, 255, 0.2)",
                    side="right"
                ),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="gray")
                )
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.warning(f"No price data available for the {selected_period} timeframe.")

# ==========================================
# 6. SENTIMENT PANELS SECTION (GRID LAYOUT)
# ==========================================
st.write("")
st.markdown("### Live Sentiment Analysis")
cols = st.columns(2)

for idx, name in enumerate(selected_names):
    data = api_responses.get(name, {})
    news = data.get("recent_news", [])
    
    pos, neg, neu = 0, 0, 0
    for article in news:
        score = article.get("Sentiment")
        if score is not None:
            score = float(score)
            if score > 0.05: pos += 1
            elif score < -0.05: neg += 1
            else: neu += 1
                     
    total_articles = pos + neg + neu
    
    with cols[idx % 2]:
        with st.container(border=True):
            logo_html = f"<img src='{get_logo(name)}' width='22' height='22' style='border-radius:50%; background:white; padding:2px; vertical-align:middle; margin-right:8px; margin-top:-4px;'>"
            st.markdown(f"#### {logo_html}{name} <span style='font-size: 12px; color: gray; margin-left: 5px; font-weight: normal;'>{TICKER_MAP.get(name, '')}</span>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: gray; font-size: 13px; min-height: 45px;'>{COMPANY_INFO.get(name, 'No description available.')}</p>", unsafe_allow_html=True)
            
            s_col1, s_col2 = st.columns([1, 1.2])
            
            with s_col1:
                st.write("")
                st.markdown("**Algorithm Rating**")
                if total_articles == 0:
                    st.markdown("<span style='color: gray; font-weight: 600;'>AWAITING DATA</span>", unsafe_allow_html=True)
                elif pos > neg:
                    st.markdown("<span style='color: #22ab59; font-size: 18px; font-weight: bold;'>BUY / BULLISH</span><br><span style='font-size:12px; color:gray;'>Positive trend detected</span>", unsafe_allow_html=True)
                elif neg > pos:
                    st.markdown("<span style='color: #ea5455; font-size: 18px; font-weight: bold;'>SELL / BEARISH</span><br><span style='font-size:12px; color:gray;'>Negative trend detected</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color: #7f7f7f; font-size: 18px; font-weight: bold;'>HOLD / NEUTRAL</span><br><span style='font-size:12px; color:gray;'>Mixed volume</span>", unsafe_allow_html=True)
                    
                st.markdown(f"<div style='margin-top: 15px; font-size: 12px; color: gray;'>Total Signals: {total_articles}</div>", unsafe_allow_html=True)

            with s_col2:
                if total_articles > 0:
                    pie_data = pd.DataFrame({
                        "Sentiment": ["Positive", "Negative", "Neutral"],
                        "Count": [pos, neg, neu]
                    })
                    pie_data = pie_data[pie_data["Count"] > 0]
                                         
                    fig_pie = px.pie(
                        pie_data, values="Count", names="Sentiment", color="Sentiment",
                        color_discrete_map={"Positive": "#22ab59", "Negative": "#ea5455", "Neutral": "#7f7f7f"},
                        hole=0.65 
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
                    fig_pie.update_layout(
                        margin=dict(t=10, b=10, l=10, r=10), height=180,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_chart_{name}_{selected_period}")
                else:
                    st.write("")
                    st.markdown("<div style='text-align: center; color: gray; padding: 40px 0;'>📊 Not enough data</div>", unsafe_allow_html=True)