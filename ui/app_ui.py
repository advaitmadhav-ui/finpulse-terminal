# ui/app_ui.py
import streamlit as st
import os
import sys

# Maintain system execution paths so imports link correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Initialize the full-width app frame
st.set_page_config(
    page_title="FinPulse Terminal", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==========================================
# 0. INJECT MINIMALIST LAYOUT + PALE HEADER CSS
# ==========================================
st.markdown("""
    <style>
    /* 1. Hide default sidebar elements */
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    
    /* 2. Clear top padding and anchor the background layer */
    .block-container { 
        max-width: 100% !important; 
        padding-top: 3.5rem !important; 
        padding-bottom: 1.5rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        position: relative; /* Acts as the anchor for the pale header */
    }

    /* 3. The Pale Header Background Panel */
    .block-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 220px; /* Safely covers the top padding, logo, and tabs */
        background-color: #171c26; /* A slightly paler, elevated dark tone */
        border-bottom: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 4px 15px rgba(0,0,0,0.35); /* Drops a 3D shadow onto the main page */
        z-index: 0;
    }

    /* Ensure actual content renders on top of the pale background */
    .block-container > div {
        position: relative;
        z-index: 1;
    }

    /* 4. Navigation Tabs Base Styling */
    div[data-testid="stButton"] > button {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: #8a92a6 !important;
        font-weight: 500 !important;
        padding: 8px 14px !important; 
        border-radius: 8px !important;
        box-shadow: none !important;
        font-size: 14.5px !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    /* Hover state for unselected tabs */
    div[data-testid="stButton"] > button:hover {
        color: #ffffff !important;
        background-color: rgba(255,255,255,0.05) !important;
    }
    
    /* 5. Active Tab Highlight (Background Fill & Glow) */
    div[data-testid="stButton"] > button[kind="primary"] {
        color: #22ab59 !important; 
        background-color: rgba(34, 171, 89, 0.1) !important; 
        border: 1px solid rgba(34, 171, 89, 0.3) !important; 
        font-weight: 700 !important;
        box-shadow: 0 0 12px rgba(34, 171, 89, 0.15) !important; 
    }
    </style>
""", unsafe_allow_html=True)

# Initialize horizontal route state tracking
if "active_page" not in st.session_state:
    st.session_state.active_page = "Home Page"

# ==========================================
# 1. HEADER: BRAND LOGO (Scaled for 50px)
# ==========================================
st.markdown(
    "<div style='display: flex; align-items: center; gap: 20px; margin-top: 0px; margin-left: 10px;'>"
    "<div style='display: flex; justify-content: center; align-items: center; width: 72px; height: 72px; background: linear-gradient(135deg, #1e2532 0%, #0e1117 100%); border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; box-shadow: 0 8px 16px rgba(0,0,0,0.6), inset 0 2px 4px rgba(255,255,255,0.08);'>"
    "<svg width='40' height='40' viewBox='0 0 24 24' fill='none' stroke='#22ab59' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
    "<polyline points='22 12 18 12 15 21 9 3 6 12 2 12'></polyline>"
    "</svg>"
    "</div>"
    "<div style='display: flex; flex-direction: column; justify-content: center;'>"
    "<span style='font-size: 50px; font-weight: 800; color: #ffffff; font-family: sans-serif; letter-spacing: -1.5px; line-height: 1.0;'>FinPulse</span>"
    "<span style='font-size: 15px; color: #8a92a6; font-weight: 700; letter-spacing: 4.5px; margin-top: 4px;'>TERMINAL</span>"
    "</div>"
    "</div>", 
    unsafe_allow_html=True
)

# ==========================================
# 2. NAVIGATION: HIGHLIGHTED TABS
# ==========================================
st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

# We use an uneven column distribution to keep the tabs tightly packed on the left
tab_cols = st.columns([1.2, 1.2, 1.0, 1.4, 4.5]) 

pages_map = {
    "Home Page": "ui/HOME_PAGE.py",
    "Compare Stocks": "ui/pages/Compare_Stocks.py",
    "Market News": "ui/pages/NEWS.py",
    "Sentiment Analytics": "ui/pages/SENTIMENT_ANALYTICS.py"
}

for i, page_title in enumerate(pages_map.keys()):
    with tab_cols[i]:
        is_active = st.session_state.active_page == page_title
        if st.button(
            page_title, 
            key=f"nav_btn_{page_title}", 
            use_container_width=True, 
            type="primary" if is_active else "secondary"
        ):
            st.session_state.active_page = page_title
            st.rerun()

# Spacer pushing the dashboard content safely below the pale header's drop shadow
st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

# ==========================================
# 3. ISOLATED RUNTIME PAGE EXECUTION
# ==========================================
target_file_path = pages_map[st.session_state.active_page]

# Build an environment dictionary so child scripts retain perfect path awareness
execution_environment = dict(globals())
execution_environment["__file__"] = os.path.abspath(target_file_path)

with open(target_file_path, "r", encoding="utf-8") as file_stream:
    file_contents = file_stream.read()
    exec(file_contents, execution_environment)