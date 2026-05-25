"""
VianaChat MVP - Main Application
An analytics chatbot that translates natural language to SQL and visualizes results.
Powered by Plotly for robust interactivity and export.
"""

import streamlit as st
import openai
import re
import pandas as pd
import io
from src.prompts import get_system_prompt
from src.chart_helpers import ChartDrawer
from src.export_helpers import generate_pdf_report

# Page Configuration
st.set_page_config(
    page_title="VianaChat - Analytics Assistant",
    page_icon="https://storage.googleapis.com/bkt-viana-dev-sso-certs-public/viana/viana22.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling to match Viana Brand
st.markdown("""
<style>
    /* Import Inter font for professional typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Apply Inter globally */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
    }
    
    /* Prevent text selection indicators on brand/UI elements for a smoother app feel */
    .header-container, .header-title, img, .stButton, [data-testid="stSidebar"], div[data-testid="stImage"] {
        user-select: none;
        -webkit-user-select: none;
    }

    /* --- VERTICAL TOOLBAR STYLING (Targeted fix) --- */
    
    /* 1. CHART ICON TOOLBAR: Target only the chart selection radio */
    div[data-testid="stRadio"]:has(input[name*="chart_select"]) > label {
        display: none !important;
    }
    
    div[data-testid="stRadio"]:has(input[name*="chart_select"]) div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 8px;
        align-items: center;
    }
    
    /* Square Icon Style for Charts Only */
    div[data-testid="stRadio"]:has(input[name*="chart_select"]) div[role="radiogroup"] > label {
        background-color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0px !important;
        margin: 0 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 45px !important; 
        height: 45px !important;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }

    /* 2. SORT ORDER BUTTONS: Fix for Ascending/Descending labels */
    div[data-testid="stRadio"]:has(input[name*="sort_order"]) div[role="radiogroup"] {
        display: flex;
        flex-direction: row !important; /* Force horizontal */
        gap: 12px;
        align-items: center;
        width: 100% !important;
    }

    div[data-testid="stRadio"]:has(input[name*="sort_order"]) div[role="radiogroup"] > label {
        width: auto !important; /* Allow width to fit text */
        height: 35px !important;
        padding: 0 15px !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
        background-color: rgba(30, 41, 59, 0.4) !important;
    }

    /* Ensure text is visible and centered for sort buttons */
    div[data-testid="stRadio"]:has(input[name*="sort_order"]) div[data-testid="stMarkdownContainer"] p {
        color: #e2e8f0 !important;
        font-size: 0.9rem !important;
        white-space: nowrap !important; /* Prevent text wrapping */
    }

    /* 3. SHARED LOGIC (Keep existing hover/check effects) */
    div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background-color: #0056D2 !important;
        border-color: #0056D2 !important;
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
        display: none !important; /* Hide original radio circles */
    }
    
    /* Ensure the entire label area is clickable */
    div[data-testid="stRadio"] div[role="radiogroup"] > label {
        user-select: none;
        -webkit-user-select: none;
    }
    
    /* Hover State */
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.05) !important; /* Very subtle hover bg */
        transform: translateY(-2px);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover p {
        color: #0056D2 !important;
    }

    /* Selected State (Using :has selector) */
    div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background-color: #0056D2 !important;
        box-shadow: 0 4px 12px rgba(0, 86, 210, 0.4) !important;
        transform: scale(1.05);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p {
        color: white !important;
        font-weight: 600;
    }

    /* Styling for the App Header Alignment */
    .header-container {
        display: flex;
        align-items: center;
        gap: 15px;
        padding-bottom: 20px;
        margin-top: -20px;
    }
    .header-title {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #ffffff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    .header-container img {
        transition: transform 0.3s ease;
    }
    .header-container img:hover {
        transform: scale(1.05);
    }
    
    .stApp {
        background-color: #0c111d;
    }
    .main .block-container {
        max-width: 1000px;
    }
    header[data-testid="stHeader"] {
        background: rgba(12, 17, 29, 0.8);
        backdrop-filter: blur(16px);
    }
    
    /* Input Box Styling - Removing Red Outline */
    .stTextInput input {
        border-color: #334155 !important;
        box-shadow: none !important;
    }
    .stTextInput input:focus {
        border-color: #0056D2 !important;
        box-shadow: 0 0 0 1px #0056D2 !important;
    }
    div[data-testid="stChatInput"] textarea {
        border-color: #334155 !important;
        box-shadow: none !important;
    }
    div[data-testid="stChatInput"] textarea:focus {
        border-color: #0056D2 !important;
        box-shadow: 0 0 0 1px #0056D2 !important;
    }

    /* --- NEW UI COMPONENTS --- */

    /* Glassmorphism Insight Card */
    .insight-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }

    /* Premium Stat Card */
    .stat-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-left: 4px solid #0056D2;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }
    .stat-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }

    /* Chat Message Bubbles */
    .stChatMessage {
        padding: 1rem !important;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: rgba(30, 41, 59, 0.2); /* User bubble tint */
        border: 1px solid rgba(148, 163, 184, 0.05);
    }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: rgba(15, 23, 42, 0.4); /* Assistant bubble tint */
        border: 1px solid rgba(0, 86, 210, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    /* Thinking State Animation */
    @keyframes pulse-glow {
        0% { opacity: 0.6; }
        50% { opacity: 1; text-shadow: 0 0 10px #0056D2; }
        100% { opacity: 0.6; }
    }
    .thinking-state {
        color: #0056D2;
        font-style: italic;
        animation: pulse-glow 1.5s infinite ease-in-out;
    }
    
    /* User and Robot Icon Colors */
    div[data-testid="stChatMessageAvatarUser"] {
        background-color: #0056D2 !important;
        color: white !important;
        box-shadow: 0 0 10px rgba(0, 86, 210, 0.5);
    }
    div[data-testid="stChatMessageAvatarAssistant"] {
        background-color: #ffffff !important;
        color: #0056D2 !important;
        border: 2px solid #0056D2;
    }
    
    /* Global Button Styling (Download & Regular) - Clean, Borderless Look */
    .stButton button, .stDownloadButton button {
        background-color: transparent !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        border-radius: 8px !important;
        color: #94a3b8 !important; /* Muted text color */
        font-weight: 600 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        padding: 0.5rem 1rem !important;
    }
    
    /* Hover State for Buttons - "Lights up" */
    .stButton button:hover, .stDownloadButton button:hover {
        background-color: rgba(30, 41, 59, 0.5) !important;
        border-color: #0056D2 !important; /* Blue border appears */
        color: #e2e8f0 !important; /* Text brightens */
        box-shadow: 0 4px 12px rgba(0, 86, 210, 0.2) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Active/Click State */
    .stButton button:active, .stDownloadButton button:active {
        background-color: #0056D2 !important;
        color: white !important;
        border-color: #0056D2 !important;
        transform: translateY(0) !important;
    }
    
    /* Metric Card Styling Override for Default Metrics */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px;
        backdrop-filter: blur(4px);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #e2e8f0 !important;
    }
    
    /* Responsive adjustments for smaller screens */
    @media (max-width: 768px) {
        .header-title {
            font-size: 1.8rem;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            flex-direction: row !important;
            flex-wrap: wrap;
            justify-content: center;
        }
    }
    
    /* Smooth scrolling for chat container */
    [data-testid="stChatMessageContainer"] {
        scroll-behavior: smooth;
    }
    
    /* Enhance table styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    /* Loading state polish */
    .stStatus {
        border-radius: 8px !important;
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(148, 163, 184, 0.1) !important;
    }
    
    /* Enhanced Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
        color: #f8fafc !important;
        font-weight: 600;
        letter-spacing: -0.01em;
    }
    
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] li {
        color: #cbd5e1 !important;
        line-height: 1.6;
    }
    
    [data-testid="stSidebar"] strong {
        color: #f1f5f9 !important;
    }
    
    [data-testid="stSidebar"] hr {
        border-color: rgba(148, 163, 184, 0.2) !important;
        margin: 1.5rem 0;
    }
    
    /* Info/Success/Warning message styling */
    .stAlert {
        border-radius: 8px !important;
        border: none !important;
        background-color: rgba(30, 41, 59, 0.6) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize OpenAI API
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Initialize session state for chat history and filters
if "messages" not in st.session_state:
    st.session_state.messages = []
if "filters" not in st.session_state:
    st.session_state.filters = {}
if "processing" not in st.session_state:
    st.session_state.processing = False
if "show_all" not in st.session_state:
    st.session_state.show_all = {}


# App Header with Custom Alignment
st.markdown("""
<div class="header-container">
    <img src="https://storage.googleapis.com/bkt-viana-dev-sso-certs-public/viana/viana22.png" width="55" style="border-radius: 8px;">
    <h1 class="header-title">VianaChat</h1>
</div>
""", unsafe_allow_html=True)

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ About")
    
    st.markdown("""
    **VianaChat** is your AI-powered analytics partner.
    
    1. **Ask**: Ask anything about your data.
    2. **Refine**: Select data points in the chart to filter.
    3. **Export**: Get your results in PDF or CSV.
    """)
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.filters = {}
        st.rerun()

# Display chat history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])
        
        # Display results and charts
        if "dataframe" in message:
            df = message["dataframe"]
            
            # --- INTELLIGENT RESULT RENDERING ---
            # Check if it's a scalar value (1 row, low column count) -> Render as KPI
            is_scalar = len(df) == 1 and len(df.columns) <= 4
            
            if is_scalar:
                # Custom Stat Card View
                cols = st.columns(len(df.columns))
                for idx, col_name in enumerate(df.columns):
                    val = df.iloc[0][col_name]
                    # Format float to 2 decimal places
                    if isinstance(val, (float, int)):
                         val_fmt = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
                    else:
                        val_fmt = str(val)
                    
                    with cols[idx]:
                        st.markdown(f"""
                        <div class="stat-card">
                            <div class="stat-label">{col_name.replace('_', ' ')}</div>
                            <div class="stat-value">{val_fmt}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            else:
                # --- INSIGHT CARD CONTAINER ---
                with st.container():
                     # --- GLOBAL SORTING LOGIC (Syncs Table & Chart) ---
                    # We fetch the sort state from the widgets below *before* they are rendered in the UI
                    # so the chart at the top can use the updated sort immediately on rerun.
                    
                    sort_col_key = f"sort_col_{i}"
                    sort_order_key = f"sort_order_{i}"
                    
                    # Defaults
                    final_sort_col = None
                    is_asc = True 
                    
                    # Attempt to get values from Session State if widgets exist
                    if sort_col_key in st.session_state:
                        selected_sort = st.session_state[sort_col_key]
                        final_sort_col = None if selected_sort == "Default (Smart Sort)" else selected_sort
                    
                    if sort_order_key in st.session_state:
                        sort_val = st.session_state[sort_order_key]
                        is_asc = (sort_val == "Ascending")
    
                    # Smart Sort Default Logic (if no explicit column selected)
                    df_sorted = df.copy()
                    if not final_sort_col:
                        for col in df_sorted.columns:
                            col_lower = col.lower()
                            # Check for time keywords but exclude IDs
                            is_time_ref = any(t in col_lower for t in ['date', 'time', 'hour', 'day', 'month', 'year', 'period', 'week'])
                            is_id = 'id' in col_lower
                            is_datetime = pd.api.types.is_datetime64_any_dtype(df_sorted[col])
                            
                            if is_datetime or (is_time_ref and not is_id):
                                final_sort_col = col
                                break
                        
                        if not final_sort_col:
                            final_sort_col = df_sorted.columns[0]
                    
                    # Apply Sort
                    try:
                        df_sorted = df_sorted.sort_values(by=final_sort_col, ascending=is_asc)
                    except Exception:
                        pass
    
                    # --- VISUALIZATION (Plotly) ---
                    chart_drawer = ChartDrawer(df_sorted) # Pass Sorted DF
                    
                    chart_col, tool_col = st.columns([0.85, 0.15])
                    
                    with tool_col:
                        # Spacer
                        st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True) 
                        
                        # Map icons to chart types
                        icon_map = {
                            "llı": "bar",
                            "∿": "line",
                            "∴": "scatter",
                            "◢": "area",
                            "●": "pie"
                        }
                        
                        # 1. Chart Type Toolbar Only (Sorted buttons removed)
                        selected_icon = st.radio(
                            "Chart Style",
                            options=list(icon_map.keys()),
                            index=0,
                            key=f"chart_select_{i}",
                            label_visibility="collapsed"
                        )
                        selected_chart_type = icon_map[selected_icon]
    
                    with chart_col:
                        # Render Chart using the pre-sorted DF
                        fig = chart_drawer.get_fig(
                            df_sorted, 
                            chart_type=selected_chart_type
                        )
                        
                        if fig:
                            # Chart Header
                            chart_title = fig.layout.title.text if fig.layout.title and fig.layout.title.text else "Data Analysis"
                            st.markdown(f"""
                            <h5 style='text-align: center; 
                                       color: #e2e8f0; 
                                       margin-bottom: 5px; 
                                       margin-top: -10px;
                                       font-weight: 600;
                                       letter-spacing: -0.01em;'>
                                {chart_title}
                            </h5>
                            """, unsafe_allow_html=True)
                            
                            fig.update_layout(title_text="", margin=dict(t=10, r=10))
    
                            # Plotly Chart
                            event_data = st.plotly_chart(
                                fig, 
                                use_container_width=True, 
                                on_select="rerun", 
                                key=f"plotly_{i}",
                                config={'displayModeBar': False}
                            )
                            
                            # Selection Filtering Logic
                            if event_data and "selection" in event_data and event_data["selection"]["points"]:
                                selected_point = event_data["selection"]["points"][0]
                                filter_val = str(selected_point.get("x", selected_point.get("label", "")))
                                
                                filter_key = f"filter_{i}"
                                if st.session_state.filters.get(filter_key) != filter_val:
                                    st.session_state.filters[filter_key] = filter_val
                                    st.toast(f"Filtering by: {filter_val}", icon="🔍")
                                    st.rerun()
                    
                    # --- APPLY FILTER (To Sorted DF) ---
                    current_filter = st.session_state.filters.get(f"filter_{i}")
                    display_df = df_sorted
                    
                    if current_filter:
                        x_col = None
                        for col in display_df.columns:
                            if pd.api.types.is_object_dtype(display_df[col]) or pd.api.types.is_datetime64_any_dtype(display_df[col]):
                                x_col = col
                                break
                        if not x_col: 
                            x_col = display_df.columns[0]
    
                        if x_col:
                            display_df = display_df[display_df[x_col].astype(str) == current_filter]
                            st.success(f"Viewing records for: **{current_filter}**")
                            if st.button("Reset View", key=f"reset_{i}"):
                                del st.session_state.filters[f"filter_{i}"]
                                st.rerun()
    
                    # --- DATA PREVIEW + TABLE CONTROLS ---
                    with st.container():
                        # Header
                        st.markdown("""
                            <h4 style='color: #e2e8f0; 
                                       font-size: 1.1rem; 
                                       margin-top: 15px; 
                                       margin-bottom: 5px;
                                       font-weight: 600;'>
                                📊 Detailed Data Preview
                            </h4>
                            """, unsafe_allow_html=True)
                        
                        # --- TABLE SORTING CONTROLS ---
                        # Placed here visually, but logic was applied at start of loop to sync graph
                        sc1, sc2, _ = st.columns([2, 1, 3])
                        
                        with sc1:
                            sort_options = ["Default (Smart Sort)"].append(list(df.columns)) if isinstance(df.columns, list) else ["Default (Smart Sort)"] + list(df.columns)
                            # We use the key defined above so state persists
                            st.selectbox("Sort By", ["Default (Smart Sort)"] + list(df.columns), key=sort_col_key)
                        
                        with sc2:
                            st.radio("Order", ["Ascending", "Descending"], horizontal=True, key=sort_order_key)
    
                        # Show/Hide Logic
                        show_all_key = f"show_all_{i}"
                        is_showing_all = st.session_state.show_all.get(show_all_key, False)
                        
                        # Status & Button
                        if len(display_df) > 5:
                            d_col1, d_col2 = st.columns([4, 1])
                            with d_col1:
                                 status_text = f"Showing all {len(display_df)} records" if is_showing_all else f"Showing top 5 of {len(display_df)} records"
                                 st.markdown(f"<p style='color: #94a3b8; margin-top: 8px; font-size: 0.9em;'>{status_text}</p>", unsafe_allow_html=True)
                            with d_col2:
                                btn_label = "Show Less" if is_showing_all else "Show All"
                                if st.button(btn_label, key=f"btn_toggle_{i}", use_container_width=True):
                                    st.session_state.show_all[show_all_key] = not is_showing_all
                                    st.rerun()
    
                        # Render Table (using the sorted DF)
                        if is_showing_all:
                            st.dataframe(display_df, use_container_width=True)
                        else:
                            st.dataframe(display_df.head(5), use_container_width=True)
    
                    # --- EXPORT BUTTONS ---
                    exp_col1, exp_col2, _ = st.columns([1.5, 1.5, 4])
                    
                    with exp_col1:
                        csv = display_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name="viana_export.csv",
                            mime="text/csv",
                            key=f"csv_{i}",
                            use_container_width=True
                        )
                    
                    with exp_col2:
                        try:
                            pdf_bytes = generate_pdf_report(display_df)
                            st.download_button(
                                label="Download PDF",
                                data=pdf_bytes,
                                file_name="viana_report.pdf",
                                mime="application/pdf",
                                key=f"pdf_{i}",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Export Error: {str(e)}")
 
# Chat input
if prompt := st.chat_input("Ask a question about your data...", disabled=st.session_state.processing):
    st.session_state.processing = True
    # Clear filters on new prompt
    st.session_state.filters = {}
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Logic to handle the prompt if it was just added
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user" and st.session_state.processing:
    last_message = st.session_state.messages[-1]
    prompt = last_message["content"]
    
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        
        # Thinking State with Animation
        message_placeholder.markdown("""
            <div class="thinking-state">
                <span>⚡ Analyzing request...</span>
            </div>
        """, unsafe_allow_html=True)
        
        full_response = ""
        
        system_prompt = get_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        for msg in st.session_state.messages[:-1][-9:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True,
                temperature=0.1,
                max_tokens=1000
            )
            
            for chunk in response:
                if hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        # Update placeholder (replacing thinking animation)
                        message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # SQL execution logic
            sql_match = re.search(r"```sql\n(.*?)\n```", full_response, re.DOTALL | re.IGNORECASE)
            
            if sql_match:
                sql_query = sql_match.group(1).strip()
                with st.status("Fetching data from Snowflake...", expanded=False) as status:
                    st.code(sql_query, language="sql")
                    try:
                        conn = st.connection("snowflake")
                        result_df = conn.query(sql_query)
                        
                        if not result_df.empty:
                            status.update(label="Data synchronized successfully!", state="complete", expanded=False)
                            st.toast("Updated results", icon="📈")
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": full_response,
                                "dataframe": result_df
                            })
                        else:
                            status.update(label="No matching records found.", state="complete", expanded=False)
                            st.warning("The query returned zero records. This might be due to a strict filter or missing data.")
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                    except Exception as e:
                        status.update(label="Execution Error", state="error", expanded=True)
                        st.error(f"SQL Error: {str(e)}")
                        st.session_state.messages.append({"role": "assistant", "content": f"I had trouble running the query: {str(e)}"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        except Exception as e:
            st.error(f"AI Assistant unavailable: {str(e)}")
            st.session_state.messages.append({"role": "assistant", "content": "The AI is currently processing and cannot respond."})
        
        finally:
            st.session_state.processing = False
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 0.8em; color: gray;'>"
    "VianaChat v2.3 | Powered by Snowflake + OpenAI + Plotly"
    "</div>",
    unsafe_allow_html=True
)