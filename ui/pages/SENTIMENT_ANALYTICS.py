# ui/sentiment_analytics.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import sys
from streamlit_autorefresh import st_autorefresh

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import TICKER_MAP

st.set_page_config(page_title="FinPulse | Sentiment Analytics", layout="wide")

# Live update feed loop every 90 seconds
st_autorefresh(interval=90000, limit=500, key="analytics_refresh")

st.title("Sentiment Analytics Engine")
st.markdown("Quantitative visualization of algorithmic sentiment distribution, historical score trends, and cross-asset momentum.")

# --- DATA AGGREGATION PIPELINE ---
@st.cache_data(ttl=30)
def fetch_analytics_dataset():
    """Gathers data across all active ticker endpoints and structures it for plotting."""
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

df_raw = fetch_analytics_dataset()

if df_raw.empty:
    st.info("🔌 Awaiting data stream propagation. Ensure backend analysis script is active.")
else:
    # --- TOP ASSET SELECTOR BAR ---
    selected_asset = st.selectbox(
        "Select Asset Focus for Trend Deep Dive", 
        options=list(TICKER_MAP.keys()),
        index=0
    )
    
    st.write("---")
    
    # Split layout into two major functional sections
    col_left, col_right = st.columns([1.8, 1.2])
    
    # --- LEFT COLUMN: TIME-SERIES SENTIMENT SHIFTS ---
    with col_left:
        st.subheader(f"{selected_asset} Historical Sentiment Path")
        
        # Filter and aggregate data for the specific chosen asset
        asset_df = df_raw[df_raw['Asset_Label'] == selected_asset].copy()
        asset_df = asset_df.sort_values('Event_Time')
        
        if asset_df.empty:
            st.info(f"Insufficient volume data compiled to map trends for {selected_asset}.")
        else:
            # Calculate a rolling 3-period average to smooth out single-headline noise
            asset_df['Rolling_Avg'] = asset_df['Sentiment'].rolling(window=3, min_periods=1).mean()
            
            # Construct a clean timeline area/line plot
            trend_fig = go.Figure()
            
            # Base zero reference line to distinguish positive/negative zones instantly
            trend_fig.add_hline(y=0.0, line_dash="dash", line_color="rgba(128,128,128,0.3)", line_width=1)
            
            trend_fig.add_trace(go.Scatter(
                x=asset_df['Event_Time'],
                y=asset_df['Rolling_Avg'],
                mode='lines+markers',
                line=dict(color="#1f77b4", width=2.5),
                marker=dict(size=5, opacity=0.8),
                name="Smoothed Sentiment Index",
                hovertemplate="<b>Score: %{y:+.2f}</b><br>Date: %{x|%b %d, %H:%M}<extra></extra>"
            ))
            
            trend_fig.update_layout(
                margin=dict(l=10, r=40, t=10, b=20),
                height=350,
                hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(color="gray", size=10)
                ),
                yaxis=dict(
                    title="Sentiment Weight",
                    titlefont=dict(color="gray", size=11),
                    gridcolor="rgba(128, 128, 128, 0.1)",
                    tickfont=dict(color="gray", size=10),
                    range=[-1.05, 1.05],
                    side="right"
                )
            )
            st.plotly_chart(trend_fig, use_container_width=True, config={'displayModeBar': False})

    # --- RIGHT COLUMN: VOLUME & RATIO DISTRIBUTION ---
    with col_right:
        st.subheader("Volume Distribution")
        
        if asset_df.empty:
            st.info("No distribution volume mapping data available.")
        else:
            # Categorize items neatly into explicit sentiment buckets
            pos_vol = len(asset_df[asset_df['Sentiment'] > 0])
            neg_vol = len(asset_df[asset_df['Sentiment'] < 0])
            neu_vol = len(asset_df[asset_df['Sentiment'] == 0])
            
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
                margin=dict(l=10, r=20, t=10, b=20),
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="rgba(128, 128, 128, 0.1)", tickfont=dict(color="gray", size=10)),
                yaxis=dict(tickfont=dict(color="gray", size=11))
            )
            st.plotly_chart(dist_fig, use_container_width=True, config={'displayModeBar': False})

    st.write("---")
    
    # --- BOTTOM SECTION: MACRO CROSS-ASSET COMPARISON LEADERBOARD ---
    st.subheader("Macro Cross-Asset Sentiment Leaderboard")
    st.markdown("Immediate comparison of aggregate average scores across all systems in your configuration matrix.")
    
    # Compute group averages to find the leaderboards
    leaderboard_df = df_raw.groupby('Asset_Label').agg({
        'Sentiment': 'mean',
        'Headline': 'count'
    }).reset_index().rename(columns={'Headline': 'Story_Count'})
    
    # Sort descending so top performers float naturally to the apex
    leaderboard_df = leaderboard_df.sort_values(by='Sentiment', ascending=True)
    
    # Assign standard colors mapping rules dynamically based on final computed score orientation
    colors = ['#22ab59' if val > 0 else '#ea5455' if val < 0 else '#7f7f7f' for val in leaderboard_df['Sentiment']]
    
    macro_fig = go.Figure(go.Bar(
        x=leaderboard_df['Sentiment'],
        y=leaderboard_df['Asset_Label'],
        orientation='h',
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>Net Sentiment: %{x:+.2f}<extra></extra>"
    ))
    
    macro_fig.update_layout(
        margin=dict(l=10, r=40, t=10, b=20),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="Net Combined Index Score",
            titlefont=dict(color="gray", size=11),
            gridcolor="rgba(128, 128, 128, 0.1)",
            tickfont=dict(color="gray", size=10),
            range=[-1.05, 1.05]
        ),
        yaxis=dict(tickfont=dict(color="gray", size=11), side="left")
    )
    
    st.plotly_chart(macro_fig, use_container_width=True, config={'displayModeBar': False})