# ui/pages/1_Compare_Stocks.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Compare Stocks", page_icon="📈", layout="wide")

st.title("📈 Stock Price & Sentiment Comparison")
st.markdown("Compare price trends and view real-time AI sentiment analysis for selected assets.")

# 1. Configuration & Dictionaries
AVAILABLE_STOCKS = {
    "Reliance Industries": "RELIANCE.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Infosys": "INFY.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Kotak Mahindra": "KOTAKBANK.NS",
    "State Bank of India": "SBIN.NS",
    "Adani Enterprises": "ADANIENT.NS"
}

# Static "About" summaries for the tracked companies
COMPANY_INFO = {
    "Reliance Industries": "An Indian multinational conglomerate with diverse businesses including energy, petrochemicals, natural gas, retail, telecommunications, and mass media.",
    "HDFC Bank": "India's largest private sector bank by assets, providing a wide range of retail banking, wholesale banking, and treasury operations.",
    "ICICI Bank": "A multinational bank and financial services company offering banking products, investment banking, life insurance, and wealth management.",
    "Infosys": "A global leader in next-generation digital services and consulting, enabling clients across the world to navigate their digital transformation.",
    "Tata Consultancy Services": "An Indian multinational IT services and consulting company, part of the Tata Group, operating in 150 locations across 46 countries.",
    "Kotak Mahindra": "An Indian banking and financial services company offering banking products, personal finance, investment banking, and wealth management.",
    "State Bank of India": "An Indian multinational, public sector banking and financial services statutory body. It is the largest bank in India.",
    "Adani Enterprises": "The flagship company of the Adani Group, focusing on incubating new businesses in sectors like infrastructure, mining, and airports."
}

all_options = list(AVAILABLE_STOCKS.keys())

# 2. Controls
select_all = st.checkbox("Select all tracked stocks")

if select_all:
    selected_names = st.multiselect("Select Stocks:", options=all_options, default=all_options)
else:
    selected_names = st.multiselect("Select Stocks:", options=all_options)

# 3. Main Logic
if not selected_names:
    st.info("👈 Please select at least one stock to view the dashboard.")
else:
    all_data = []
    api_responses = {} # Store responses so we don't hit the API twice!
    
    with st.spinner("Fetching synchronized data from FinPulse API..."):
        for name in selected_names:
            ticker = AVAILABLE_STOCKS[name]
            try:
                response = requests.get(f"http://127.0.0.1:8000/api/data/{ticker}")
                if response.status_code == 200:
                    data = response.json()
                    api_responses[name] = data # Save for the sentiment panels
                    time_series = data.get("time_series", [])
                    
                    if time_series:
                        df = pd.DataFrame(time_series)
                        price_col = next((col for col in df.columns if col.lower() == 'close'), None)
                        date_col = next((col for col in df.columns if col.lower() in ['datetime_str', 'timestamp', 'datetime']), None)
                        
                        if price_col and date_col:
                            df['Stock'] = name
                            df['Datetime'] = df[date_col]
                            df['Price'] = df[price_col]
                            all_data.append(df[['Datetime', 'Price', 'Stock']])
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to the backend API. Ensure Uvicorn is running.")
                break

    # --- PRICE CHART SECTION ---
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df['Datetime'] = pd.to_datetime(combined_df['Datetime'], errors='coerce', utc=True)
        combined_df['Price'] = pd.to_numeric(combined_df['Price'], errors='coerce')
        combined_df['Stock'] = combined_df['Stock'].astype(str)
        combined_df = combined_df.dropna(subset=['Datetime', 'Price', 'Stock'])
        
        if not combined_df.empty:
            fig = go.Figure()
            unique_stocks = combined_df['Stock'].unique()
            
            for stock_name in unique_stocks:
                stock_data = combined_df[combined_df['Stock'] == stock_name].sort_values('Datetime')
                fig.add_trace(go.Scatter(
                    x=stock_data['Datetime'], y=stock_data['Price'], mode='lines', name=stock_name
                ))
            
            fig.update_layout(title="Relative Price Movement", xaxis_title="Time", yaxis_title="Closing Price (₹)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

# --- SENTIMENT PANELS SECTION ---
    st.markdown("---")
    st.subheader("📰 Sentiment Analysis & Recommendations")
    
    for name in selected_names:
        data = api_responses.get(name, {})
        news = data.get("recent_news", [])
        
        with st.container():
            st.markdown(f"### {name}")
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.markdown("**About the Company:**")
                st.write(COMPANY_INFO.get(name, "No description available."))
                
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
                
                st.markdown("**AI Recommendation:**")
                if total_articles == 0:
                    st.warning("No recent news scored for this asset yet.")
                elif pos > neg:
                    st.success("📈 **BUY / BULLISH** (Positive news trend detected)")
                elif neg > pos:
                    st.error("📉 **SELL / BEARISH** (Negative news trend detected)")
                else:
                    st.info("⚖️ **HOLD / NEUTRAL** (Mixed or neutral news volume)")

            with col2:
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
                            "Positive": "#28a745",
                            "Negative": "#dc3545",
                            "Neutral": "#6c757d"
                        },
                        hole=0.4
                    )
                    fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
                    
                    # --- ADDED UNIQUE KEY HERE TO RESOLVE DUPLICATE ID ERROR ---
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_chart_{name}")
                else:
                    st.write("📊 *Not enough data for chart.*")
            
            st.markdown("<hr style='border:1px solid #f0f2f6'>", unsafe_allow_html=True)