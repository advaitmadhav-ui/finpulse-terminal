# ui/pages/1_Compare_Stocks.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import sys

# System path expansion to link to config
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
        
        /* Smooth Borders and Backgrounds */
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            background-color: #111520 !important; /* Darker card background */
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        
        /* Multi-Select Styling */
        .stMultiSelect div[data-baseweb="select"] {
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
st.markdown("## 📊 Stock Price & Sentiment Comparison")
st.markdown("<span style='color: gray; font-size: 14px;'>Compare normalized price trends and view real-time AI sentiment analysis across multiple assets.</span>", unsafe_allow_html=True)
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

all_options = list(TICKER_MAP.keys())

# ==========================================
# 2. CONTROLS
# ==========================================
col_sel1, col_sel2 = st.columns([3, 1])
with col_sel1:
    selected_names = st.multiselect(
        "Select Stocks to Compare:", 
        options=all_options,  
        label_visibility="collapsed", 
        placeholder="Select assets to add to comparison..."
    )
with col_sel2:
    st.write("")
    select_all = st.checkbox("Select all tracked stocks")
    if select_all:
        selected_names = all_options

st.write("---")

# ==========================================
# 3. MAIN LOGIC & DATA FETCHING
# ==========================================
if not selected_names:
    st.info("💡 Please select at least one stock to view the dashboard.")
else:
    all_data = []
    api_responses = {} 
         
    with st.spinner("Fetching synchronized data from FinPulse API..."):
        for name in selected_names:
            ticker = TICKER_MAP[name]
            try:
                response = requests.get(f"http://127.0.0.1:8000/api/data/{ticker}")
                if response.status_code == 200:
                    data = response.json()
                    api_responses[name] = data 
                    time_series = data.get("time_series", [])
                                         
                    if time_series:
                        df = pd.DataFrame(time_series)
                        price_col = next((col for col in df.columns if col.lower() == 'close'), None)
                        date_col = next((col for col in df.columns if col.lower() in ['datetime_str', 'timestamp', 'datetime']), None)
                                                 
                        if price_col and date_col:
                            df['Stock'] = name
                            df['Datetime'] = df[date_col]
                            df['Price'] = df[price_col]
                            
                            # NORMALIZATION LOGIC: Start all stocks at exactly 100 for fair visual comparison
                            start_price = df['Price'].iloc[0]
                            df['Normalized_Price'] = (df['Price'] / start_price) * 100 if start_price != 0 else 100
                            
                            all_data.append(df[['Datetime', 'Price', 'Normalized_Price', 'Stock']])
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to the backend API. Ensure Uvicorn is running.")
                break

    # ==========================================
    # 4. PRICE CHART SECTION (NORMALIZED)
    # ==========================================
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df['Datetime'] = pd.to_datetime(combined_df['Datetime'], errors='coerce', utc=True)
        combined_df['Price'] = pd.to_numeric(combined_df['Price'], errors='coerce')
        combined_df['Stock'] = combined_df['Stock'].astype(str)
        combined_df = combined_df.dropna(subset=['Datetime', 'Price', 'Stock'])
                 
        if not combined_df.empty:
            st.markdown("### 📈 Relative Price Movement (Indexed to 100%)")
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
                             
                fig.update_layout(
                    margin=dict(l=10, r=20, t=20, b=20),
                    height=450,
                    hovermode="x unified",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False, tickfont=dict(color="gray", size=10)),
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
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(color="gray")
                    )
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # ==========================================
    # 5. SENTIMENT PANELS SECTION (GRID LAYOUT)
    # ==========================================
    st.write("")
    st.markdown("### Sentiment & Recommendations")
         
    # Create a 2-column masonry grid
    cols = st.columns(2)
    
    for idx, name in enumerate(selected_names):
        data = api_responses.get(name, {})
        news = data.get("recent_news", [])
        
        # Calculate Sentiment
        pos, neg, neu = 0, 0, 0
        for article in news:
            score = article.get("Sentiment")
            if score is not None:
                score = float(score)
                if score > 0.05: pos += 1
                elif score < -0.05: neg += 1
                else: neu += 1
                         
        total_articles = pos + neg + neu
        
        # Alternate between the left and right columns
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"#### {name} <span style='font-size: 12px; color: gray; margin-left: 5px;'>{TICKER_MAP.get(name, '')}</span>", unsafe_allow_html=True)
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
                            pie_data, 
                            values="Count", 
                            names="Sentiment", 
                            color="Sentiment",
                            color_discrete_map={
                                "Positive": "#22ab59",
                                "Negative": "#ea5455",
                                "Neutral": "#7f7f7f"
                            },
                            hole=0.65 # Upgraded to a sleek donut chart
                        )
                        # Hide the messy legend and place labels directly inside the donut
                        fig_pie.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
                        fig_pie.update_layout(
                            margin=dict(t=10, b=10, l=10, r=10), 
                            height=180,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)"
                        )
                                             
                        st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_chart_{name}")
                    else:
                        st.write("")
                        st.markdown("<div style='text-align: center; color: gray; padding: 40px 0;'>📊 Not enough data</div>", unsafe_allow_html=True)