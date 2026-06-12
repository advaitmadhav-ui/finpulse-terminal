# ui/pages/SENTIMENT_ANALYTICS.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import os
import sys
from streamlit_autorefresh import st_autorefresh

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_MAP

# Auto-refresh interval
st_autorefresh(interval=90000, limit=500, key="analytics_refresh")

st.markdown("## 🧠 Sentiment Analytics Engine")
st.markdown("<span style='color: gray; font-size: 14px;'>Quantitative visualization of algorithmic sentiment distribution, price correlation, and cross-asset momentum.</span>", unsafe_allow_html=True)
st.write("")

# ==========================================
# 1. CORE DATA AGGREGATION
# ==========================================
@st.cache_data(ttl=30)
def fetch_analytics_dataset():
    all_news = []
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
                    all_news.append(item)
        except Exception:
            continue
                 
    if not all_news:
        return pd.DataFrame()
             
    df = pd.DataFrame(all_news)
    df['Sentiment'] = pd.to_numeric(df['Sentiment'], errors='coerce')
    df['Event_Time'] = pd.to_datetime(df['Event_Time'])
    df = df.drop_duplicates(subset=['Headline', 'Event_Time'])
    return df

@st.cache_data(ttl=300)
def fetch_price_history(ticker):
    """Fetches the last 3 months of daily price data for correlation mapping."""
    try:
        df = yf.Ticker(ticker).history(period="3mo")
        df = df.reset_index()
        # Handle timezone awareness issues
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        df['DateOnly'] = df['Date'].dt.date
        return df
    except Exception:
        return pd.DataFrame()

df_raw = fetch_analytics_dataset()

# ==========================================
# 2. MAIN DASHBOARD RENDER
# ==========================================
if df_raw.empty:
    st.info("⏳ Awaiting data stream propagation. Ensure backend analysis script is active.")
else:
    # Top Control Filter
    selected_asset = st.selectbox(
        "Select Asset Focus for Trend Deep Dive", 
        options=list(TICKER_MAP.keys()),
        index=0
    )
    selected_ticker = TICKER_MAP[selected_asset]
         
    st.write("---")
    col_left, col_right = st.columns([2.2, 1.1])
         
    with col_left:
        st.markdown(f"### 📈 {selected_asset} Price vs Sentiment Correlation")
                 
        asset_df = df_raw[df_raw['Asset_Label'] == selected_asset].copy()
        price_df = fetch_price_history(selected_ticker)
                 
        if asset_df.empty or price_df.empty:
            st.info(f"Insufficient volume data compiled to map correlation trends for {selected_asset}.")
        else:
            # 1. Process Sentiment Data into Daily Averages
            asset_df['DateOnly'] = asset_df['Event_Time'].dt.date
            daily_sentiment = asset_df.groupby('DateOnly')['Sentiment'].mean().reset_index()
            daily_sentiment['Rolling_Avg'] = daily_sentiment['Sentiment'].rolling(window=3, min_periods=1).mean()
            
           

            # 3. Build Dual-Axis Plotly Chart
            with st.container(border=True):
                trend_fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                currency = "$" if ".NS" not in selected_ticker else "₹"
                
                # Trace 1: Stock Price (Primary Y-Axis - Green)
                trend_fig.add_trace(go.Scatter(
                    x=price_df['Date'],
                    y=price_df['Close'],
                    mode='lines',
                    line=dict(color="#22ab59", width=2.5),
                    name="Stock Price",
                    hovertemplate=f"<b>Price: {currency}%{{y:.2f}}</b><extra></extra>"
                ), secondary_y=False)
                
                # Trace 2: Sentiment Score (Secondary Y-Axis - Purple/Blue)
                trend_fig.add_trace(go.Scatter(
                    x=daily_sentiment['DateOnly'],
                    y=daily_sentiment['Rolling_Avg'],
                    mode='lines+markers',
                    line=dict(color="#9467bd", width=2, dash="dot"),
                    marker=dict(size=6, color="#9467bd", opacity=0.8),
                    name="Sentiment (3D Avg)",
                    hovertemplate="<b>Sentiment: %{y:+.2f}</b><extra></extra>"
                ), secondary_y=True)
                
                # Base Line for Neutral Sentiment (0.0)
                trend_fig.add_hline(y=0.0, line_dash="solid", line_color="rgba(128,128,128,0.2)", line_width=1, secondary_y=True)

                trend_fig.update_layout(
                    margin=dict(l=10, r=10, t=10, b=20),
                    height=380,
                    hovermode="x unified",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="gray")),
                    xaxis=dict(showgrid=False, tickfont=dict(color="gray", size=10)),
                )
                
                # Update Y-Axes specific styling
                trend_fig.update_yaxes(
                    title_text=f"Closing Price ({currency})", 
                    titlefont=dict(color="#22ab59", size=11),
                    tickfont=dict(color="#22ab59", size=10),
                    gridcolor="rgba(128, 128, 128, 0.05)",
                    secondary_y=False
                )
                trend_fig.update_yaxes(
                    title_text="Sentiment Score (-1 to 1)", 
                    titlefont=dict(color="#9467bd", size=11),
                    tickfont=dict(color="#9467bd", size=10),
                    showgrid=False,
                    range=[-1.05, 1.05],
                    secondary_y=True
                )
                
                st.plotly_chart(trend_fig, use_container_width=True, config={'displayModeBar': False})

    with col_right:
        st.markdown("### 📊 Volume Distribution")
                 
        if asset_df.empty:
            st.info("No distribution volume mapping data available.")
        else:
            with st.container(border=True):
                pos_vol = len(asset_df[asset_df['Sentiment'] > 0.05])
                neg_vol = len(asset_df[asset_df['Sentiment'] < -0.05])
                neu_vol = len(asset_df[(asset_df['Sentiment'] >= -0.05) & (asset_df['Sentiment'] <= 0.05)])
                             
                dist_df = pd.DataFrame({
                    'Classification': ['Bullish', 'Neutral', 'Bearish'],
                    'Volume Count': [pos_vol, neu_vol, neg_vol],
                    'Color_Map': ['#22ab59', '#7f7f7f', '#ea5455']
                })
                             
                dist_fig = go.Figure(go.Bar(
                    x=dist_df['Volume Count'],
                    y=dist_df['Classification'],
                    orientation='h',
                    marker_color=dist_df['Color_Map'],
                    hovertemplate="<b>%{y} Vol: %{x} articles</b><extra></extra>"
                ))
                             
                dist_fig.update_layout(
                    margin=dict(l=10, r=20, t=20, b=20),
                    height=380,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(gridcolor="rgba(128, 128, 128, 0.1)", tickfont=dict(color="gray", size=10)),
                    yaxis=dict(tickfont=dict(color="gray", size=11))
                )
                st.plotly_chart(dist_fig, use_container_width=True, config={'displayModeBar': False})

    st.write("---")
         
    # ==========================================
    # 3. MACRO LEADERBOARD
    # ==========================================
    st.markdown("### 🏆 Macro Cross-Asset Sentiment Leaderboard")
    st.markdown("<span style='color: gray; font-size: 13px;'>Immediate comparison of aggregate average scores across all systems in your configuration matrix.</span>", unsafe_allow_html=True)
    st.write("")
         
    leaderboard_df = df_raw.groupby('Asset_Label').agg({
        'Sentiment': 'mean',
        'Headline': 'count'
    }).reset_index().rename(columns={'Headline': 'Story_Count'})
         
    leaderboard_df = leaderboard_df.sort_values(by='Sentiment', ascending=True)
    colors = ['#22ab59' if val > 0.05 else '#ea5455' if val < -0.05 else '#7f7f7f' for val in leaderboard_df['Sentiment']]
         
    with st.container(border=True):
        macro_fig = go.Figure(go.Bar(
            x=leaderboard_df['Sentiment'],
            y=leaderboard_df['Asset_Label'],
            orientation='h',
            marker_color=colors,
            hovertemplate="<b>%{y}</b><br>Net Sentiment: %{x:+.2f}<extra></extra>"
        ))
             
        macro_fig.update_layout(
            margin=dict(l=10, r=40, t=20, b=20),
            height=350,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                title="Net Combined Index Score",
                titlefont=dict(color="gray", size=11),
                gridcolor="rgba(128, 128, 128, 0.1)",
                tickfont=dict(color="gray", size=10),
                range=[-1.05, 1.05]
            ),
            yaxis=dict(tickfont=dict(color="gray", size=12), side="left")
        )
             
        st.plotly_chart(macro_fig, use_container_width=True, config={'displayModeBar': False})