# ui/pages/SENTIMENT_ANALYTICS.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import os
import sys
import urllib.parse 
import datetime
from streamlit_autorefresh import st_autorefresh

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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

st_autorefresh(interval=60000, limit=500, key="analytics_refresh")

def inject_custom_css():
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            border-radius: 12px !important; border: 1px solid rgba(255, 255, 255, 0.05) !important;
            background-color: #111520 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stVerticalBlock"] > div[style*="border"]:hover {
            transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.4); border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        .stSelectbox div[data-baseweb="select"] { background-color: #111520 !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 8px !important; }
        .snapshot-metric-label { color: #8a92a6; font-size: 13px; margin-bottom: 2px; }
        .snapshot-metric-value { font-size: 18px; font-weight: bold; margin-bottom: 15px; }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

@st.cache_data(ttl=60)
def fetch_analytics_dataset():
    all_news = []
    for label, ticker in TICKER_MAP.items():
        safe_ticker = urllib.parse.quote(ticker)
        API_ENDPOINT = f"http://127.0.0.1:8000/api/data/{safe_ticker}"
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
                 
    if not all_news: return pd.DataFrame()
             
    df = pd.DataFrame(all_news)
    df['Sentiment'] = pd.to_numeric(df['Sentiment'], errors='coerce')
    df['Event_Time'] = pd.to_datetime(df['Event_Time'])
    df = df.drop_duplicates(subset=['Headline', 'Event_Time'])
    return df

@st.cache_data(ttl=300)
def fetch_price_history(ticker):
    try:
        df = yf.Ticker(urllib.parse.quote(ticker)).history(period="1y")
        df = df.reset_index()
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        df['DateOnly'] = df['Date'].dt.date
        
        if ".NS" not in ticker:
            try:
                fx_rate = yf.Ticker("INR=X").history(period="1d")['Close'].iloc[-1]
            except Exception:
                fx_rate = 83.50
            df['Close'] = df['Close'] * fx_rate
            
        return df
    except Exception:
        return pd.DataFrame()

df_raw = fetch_analytics_dataset()

if df_raw.empty:
    st.info("⏳ Awaiting data stream propagation. Ensure backend analysis script is active.")
else:
    top_col1, top_col2 = st.columns([1.5, 1.1])
    
    with top_col1:
        st.markdown("""
            <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 20px;'>
                <div style='font-size: 40px;'>🧠</div>
                <div><h2 style='margin: 0; padding: 0;'>Sentiment Analytics Engine</h2>
                <span style='color: gray; font-size: 14px;'>Quantitative visualization of algorithmic sentiment distribution, price correlation, and cross-asset momentum.</span></div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        st.markdown("<span style='color: gray; font-size: 12px;'>Select Asset Focus for Trend Deep Dive</span>", unsafe_allow_html=True)
        selected_asset = st.selectbox("Asset Focus", options=list(TICKER_MAP.keys()), index=0, label_visibility="collapsed")
        selected_ticker = TICKER_MAP[selected_asset]

    asset_df = df_raw[df_raw['Asset_Label'] == selected_asset].copy()
    price_df = fetch_price_history(selected_ticker)
    
    latest_score, correlation_val, confidence = 0.0, 0.0, 0
    
    if not asset_df.empty:
        asset_df['DateOnly'] = asset_df['Event_Time'].dt.date
        daily_sentiment = asset_df.groupby('DateOnly')['Sentiment'].mean().reset_index()
        daily_sentiment['Rolling_Avg'] = daily_sentiment['Sentiment'].rolling(window=3, min_periods=1).mean()
        latest_score = daily_sentiment['Rolling_Avg'].iloc[-1] if not daily_sentiment.empty else 0.0
        
        if not price_df.empty:
            merged_df = pd.merge(price_df, daily_sentiment, on='DateOnly', how='inner')
            if len(merged_df) > 2: correlation_val = merged_df['Close'].corr(merged_df['Rolling_Avg'])
                
        pos_vol = len(asset_df[asset_df['Sentiment'] > 0.05])
        neg_vol = len(asset_df[asset_df['Sentiment'] < -0.05])
        total_vol = len(asset_df)
        confidence = int(((pos_vol + neg_vol) / total_vol) * 100) if total_vol > 0 else 0

    with top_col2:
        with st.container(border=True):
            st.markdown("##### Asset Sentiment Snapshot ⓘ")
            
            if latest_score > 0.05: mood, color = "Bullish", "#22ab59"
            elif latest_score < -0.05: mood, color = "Bearish", "#ea5455"
            else: mood, color = "Neutral", "#7f7f7f"
            
            if abs(correlation_val) > 0.5: trend_str, trend_color = "Strong", "#22ab59"
            elif abs(correlation_val) > 0.2: trend_str, trend_color = "Moderate", "#f39c12"
            else: trend_str, trend_color = "Weak", "#ea5455"
            
            snap_l, snap_r = st.columns([1.2, 1])
            with snap_l:
                st.markdown("<div style='color: gray; font-size: 12px;'>Overall Sentiment</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='color: {color}; font-size: 28px; font-weight: bold;'>{mood}</div>", unsafe_allow_html=True)
                
                gauge_fig = go.Figure(go.Indicator(
                    mode="gauge", value=latest_score,
                    gauge={
                        'axis': {'range': [-1, 1], 'visible': False}, 'bar': {'color': color, 'thickness': 0.75},
                        'bgcolor': "rgba(255,255,255,0.05)", 'shape': "angular"
                    }
                ))
                gauge_fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=100, paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(gauge_fig, use_container_width=True, config={'displayModeBar': False})
                
            with snap_r:
                st.markdown(f"<div class='snapshot-metric-label'>Sentiment Score</div><div class='snapshot-metric-value' style='color: {color};'>{latest_score:+.2f}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='snapshot-metric-label'>Trend Strength</div><div class='snapshot-metric-value' style='color: {trend_color};'>{trend_str}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='snapshot-metric-label'>Confidence</div><div class='snapshot-metric-value' style='color: #22ab59;'>{confidence}%</div>", unsafe_allow_html=True)

    st.write("")

    col_chart, col_vol = st.columns([2.2, 1.1])
         
    with col_chart:
        with st.container(border=True):
            header_col, pill_col = st.columns([2, 1.5])
            with header_col:
                logo_html = f"<img src='{get_logo(selected_asset)}' width='24' height='24' style='border-radius:50%; background:white; padding:2px; vertical-align:middle; margin-right:8px; margin-top:-4px;'>"
                st.markdown(f"#### {logo_html}{selected_asset}: Price vs Sentiment ⓘ", unsafe_allow_html=True)
            with pill_col:
                selected_tf = st.pills("Timeframe", options=["1M", "3M", "6M", "1Y", "ALL"], default="3M", label_visibility="collapsed")

            if asset_df.empty or price_df.empty:
                st.info(f"Insufficient volume data compiled to map correlation trends for {selected_asset}.")
            else:
                cutoff_date = None
                latest_date = price_df['DateOnly'].max()
                if selected_tf == "1M": cutoff_date = latest_date - datetime.timedelta(days=30)
                elif selected_tf == "3M": cutoff_date = latest_date - datetime.timedelta(days=90)
                elif selected_tf == "6M": cutoff_date = latest_date - datetime.timedelta(days=180)
                elif selected_tf == "1Y": cutoff_date = latest_date - datetime.timedelta(days=365)
                
                plot_price_df = price_df[price_df['DateOnly'] >= cutoff_date] if cutoff_date else price_df
                plot_sent_df = daily_sentiment[daily_sentiment['DateOnly'] >= cutoff_date] if cutoff_date else daily_sentiment

                if correlation_val > 0.5: corr_color, corr_text = "#22ab59", "Strong Positive Correlation"
                elif correlation_val > 0: corr_color, corr_text = "#22ab59", "Weak Positive Correlation"
                elif correlation_val < -0.5: corr_color, corr_text = "#ea5455", "Strong Negative Correlation"
                elif correlation_val < 0: corr_color, corr_text = "#ea5455", "Weak Negative Correlation"
                else: corr_color, corr_text = "#7f7f7f", "No Meaningful Correlation"

                st.markdown(f"""
                    <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 10px;'>
                        <div style='font-size: 13px;'><span style='color: gray;'>Pearson Coefficient:</span> 
                        <b style='color: {corr_color}; margin-left: 5px;'>{correlation_val:+.2f}</b></div>
                        <div style='color: gray; font-size: 12px;'>{corr_text}</div>
                    </div>
                """, unsafe_allow_html=True)

                if st.button("🏛️ View Fundamental Health Rankings", type="secondary", use_container_width=True):
                    st.session_state.selected_asset = None 
                    st.session_state.active_page = "Home Page"
                    st.rerun()
                    
                st.write("")

                trend_fig = make_subplots(specs=[[{"secondary_y": True}]])
                currency = "₹"
                
                trend_fig.add_trace(go.Scatter(
                    x=plot_price_df['Date'], y=plot_price_df['Close'], mode='lines',
                    line=dict(color="#22ab59", width=2.5), name=f"Stock Price ({currency})",
                    hovertemplate=f"<b>Price: {currency}%{{y:.2f}}</b><extra></extra>"
                ), secondary_y=False)
                
                trend_fig.add_trace(go.Scatter(
                    x=plot_sent_df['DateOnly'], y=plot_sent_df['Rolling_Avg'], mode='lines+markers',
                    line=dict(color="#9467bd", width=2, dash="dot"), marker=dict(size=5, color="#9467bd", opacity=0.8),
                    name="Sentiment (3D Avg)", hovertemplate="<b>Sentiment: %{y:+.2f}</b><extra></extra>"
                ), secondary_y=True)
                
                trend_fig.add_hline(y=0.0, line_dash="solid", line_color="rgba(128,128,128,0.2)", line_width=1, secondary_y=True)

                trend_fig.update_layout(
                    margin=dict(l=10, r=10, t=30, b=20), height=350, hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(color="gray")),
                    xaxis=dict(showgrid=False, tickfont=dict(color="gray", size=10)),
                )
                
                trend_fig.update_yaxes(title_text=f"Closing Price ({currency})", titlefont=dict(color="#22ab59", size=11), tickfont=dict(color="#22ab59", size=10), gridcolor="rgba(128, 128, 128, 0.05)", secondary_y=False)
                trend_fig.update_yaxes(title_text="Sentiment Score", titlefont=dict(color="#9467bd", size=11), tickfont=dict(color="#9467bd", size=10), showgrid=False, range=[-1.05, 1.05], secondary_y=True)
                st.plotly_chart(trend_fig, use_container_width=True, config={'displayModeBar': False})
                st.caption("Sentiment score is normalized between -1 (Very Bearish) to +1 (Very Bullish)")

    with col_vol:
        with st.container(border=True):
            st.markdown("#### 📊 Volume Distribution ⓘ")
            st.write("")
                 
            if asset_df.empty:
                st.info("No distribution volume mapping data available.")
            else:
                neu_vol = total_vol - pos_vol - neg_vol
                dist_fig = go.Figure(go.Pie(
                    labels=['Bullish', 'Neutral', 'Bearish'], values=[pos_vol, neu_vol, neg_vol], hole=0.6,
                    marker_colors=['#22ab59', '#7f7f7f', '#ea5455'], textinfo='percent', textfont=dict(color='white', size=12),
                    hovertemplate="<b>%{label}</b><br>Volume: %{value}<extra></extra>"
                ))
                dist_fig.update_layout(margin=dict(l=20, r=20, t=10, b=10), height=240, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(dist_fig, use_container_width=True, config={'displayModeBar': False})
                
                st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; font-size: 13px; color: gray; margin-bottom: 8px;'>
                        <div><span style='color: #ea5455;'>■</span> Bearish</div> <div>{neg_vol} items</div> <div>{int((neg_vol/total_vol)*100)}%</div>
                    </div>
                    <div style='display: flex; justify-content: space-between; font-size: 13px; color: gray; margin-bottom: 8px;'>
                        <div><span style='color: #7f7f7f;'>■</span> Neutral</div> <div>{neu_vol} items</div> <div>{int((neu_vol/total_vol)*100)}%</div>
                    </div>
                    <div style='display: flex; justify-content: space-between; font-size: 13px; color: gray; margin-bottom: 15px;'>
                        <div><span style='color: #22ab59;'>■</span> Bullish</div> <div>{pos_vol} items</div> <div>{int((pos_vol/total_vol)*100)}%</div>
                    </div>
                    <hr style='margin: 10px 0; border-color: rgba(255,255,255,0.05);'>
                    <div style='display: flex; justify-content: space-between; font-size: 13px;'>
                        <div style='color: gray;'>Total Stream Volume</div> <div style='font-weight: bold;'>{total_vol} items</div>
                    </div>
                """, unsafe_allow_html=True)

    st.write("---")
         
    with st.container(border=True):
        lead_header, lead_tabs = st.columns([2, 1])
        with lead_header:
            st.markdown("### 🏆 Macro Cross-Asset Sentiment Leaderboard ⓘ")
            st.caption("Immediate comparison of aggregate average scores across all systems in your configuration matrix. Click a row or bar to view detailed metrics.")
            
        leaderboard_df = df_raw.groupby('Asset_Label').agg({'Sentiment': 'mean', 'Headline': 'count'}).reset_index().rename(columns={'Headline': 'Story_Count'})
        leaderboard_df = leaderboard_df.sort_values(by='Sentiment', ascending=True)
        colors = ['#22ab59' if val > 0.05 else '#ea5455' if val < -0.05 else '#7f7f7f' for val in leaderboard_df['Sentiment']]
        
        tab_score, tab_data = st.tabs(["Score View", "Table View"])
        
        with tab_score:
            macro_fig = go.Figure(go.Bar(
                x=leaderboard_df['Sentiment'], y=leaderboard_df['Asset_Label'], orientation='h', marker_color=colors,
                text=leaderboard_df['Sentiment'].apply(lambda x: f"{x:+.2f}"), textposition='auto', hovertemplate="<b>%{y}</b><br>Net Sentiment: %{x:+.2f}<extra></extra>"
            ))
            macro_fig.update_layout(
                margin=dict(l=10, r=40, t=10, b=20), height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Net Combined Index Score", titlefont=dict(color="gray", size=11), gridcolor="rgba(128, 128, 128, 0.1)", tickfont=dict(color="gray", size=10), range=[-1.05, 1.05]),
                yaxis=dict(tickfont=dict(color="gray", size=12), side="left")
            )
            
            chart_event = st.plotly_chart(
                macro_fig, use_container_width=True, config={'displayModeBar': False}, on_select="rerun", selection_mode="points", key="sentiment_macro_chart"
            )
            if chart_event and len(chart_event.selection.get("points", [])) > 0:
                selected_asset = chart_event.selection["points"][0].get("y")
                if selected_asset in TICKER_MAP:
                    st.session_state.selected_asset = selected_asset
                    st.session_state.active_page = "Home Page"
                    st.rerun()
            
        with tab_data:
            display_df = leaderboard_df.sort_values(by='Sentiment', ascending=False)
            display_df.insert(0, 'Logo', display_df['Asset_Label'].apply(get_logo))
            
            table_event = st.dataframe(
                display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="sentiment_macro_table",
                column_config={
                    "Logo": st.column_config.ImageColumn("", width="small"),
                    "Asset_Label": st.column_config.TextColumn("Tracked Asset"),
                    "Sentiment": st.column_config.ProgressColumn("Net Sentiment Score", format="%.3f", min_value=-1.0, max_value=1.0),
                    "Story_Count": st.column_config.NumberColumn("Volume (Analyzed Articles)")
                }
            )
            if table_event and len(table_event.selection.get("rows", [])) > 0:
                selected_row_idx = table_event.selection["rows"][0]
                selected_asset = display_df.iloc[selected_row_idx]['Asset_Label']
                if selected_asset in TICKER_MAP:
                    st.session_state.selected_asset = selected_asset
                    st.session_state.active_page = "Home Page"
                    st.rerun()