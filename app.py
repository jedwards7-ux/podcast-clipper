import os
import time
import feedparser
import requests
import streamlit as st
from google import genai
import urllib.parse

# Setup Gemini Client
client = genai.Client()

# --- STATE MANAGEMENT ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "favorites" not in st.session_state:
    st.session_state.favorites = {} 
if "active_podcast" not in st.session_state:
    st.session_state.active_podcast = None
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "current_view" not in st.session_state:
    st.session_state.current_view = "Discover"

# --- UI & MOBILE CSS CHASSIS ---
st.set_page_config(page_title="PodBrief", layout="centered")

if st.session_state.dark_mode:
    bg_color, card_bg, text_color, accent_color, border_color = "#121212", "#1E1E1E", "#FFFFFF", "#BB86FC", "#2C2C2C"
else:
    bg_color, card_bg, text_color, accent_color, border_color = "#F8F9FA", "#FFFFFF", "#212529", "#6200EE", "#E0E0E0"

st.markdown(f"""
    <style>
        .main .block-container {{ max-width: 460px !important; padding: 1rem !important; background-color: {bg_color}; color: {text_color}; }}
        .stApp {{ background-color: {bg_color}; }}
        .mobile-card {{ background-color: {card_bg}; border: 1px solid {border_color}; border-radius: 16px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        
        .stButton>button {{
            width: 100% !important;
            border-radius: 24px !important;
            border: 2px solid {accent_color} !important;
            background-color: {accent_color} !important;
            color: white !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            padding: 12px 24px !important;
            box-shadow: 0 4px 12px rgba(0,0,0, 0.2) !important;
            transition: all 0.2s ease !important;
        }}
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0, 0.3) !important;
            filter: brightness(1.15);
        }}
        
        .stTextInput>div>div>input, .stSelectbox>div>div>div {{ border-radius: 12px !important; background-color: {card_bg} !important; color: {text_color} !important; }}
        h1, h2, h3, h4, p, span, label {{ color: {text_color} !important; }}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_title, col_toggle = st.columns([0.75, 0.25])
with col_title:
    st.title("🎙️ PodBrief")
with col_toggle:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# --- TOP NAVIGATION ---
nav = st.radio("Navigation", ["🔍 Discover", "⭐ Favorites", "🎧 Player"], horizontal=True, label_visibility="collapsed")

# --- TAB 1: DISCOVER (SEARCH) ---
if nav == "🔍 Discover":
    st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
    query = st.text_input("Search podcasts (e.g. Comedy, Fantasy Sports):")
    if st.button("Search iTunes Directory"):
        with st.spinner("Searching..."):
            safe_query = urllib.parse.quote(query)
            url = f"https://itunes.apple.com/search?term={safe_query}&media=podcast&limit=15"
            resp = requests.get(url)
            if resp.status_code == 200:
                st.session_state.search_results = resp.json().get('results', [])
    st.markdown('</div>', unsafe_allow_html=True)

    for pod in st.session_state.search_results:
        title = pod.get('collectionName', 'Unknown Title')
        feed_url = pod.get('feedUrl')
        img_url = pod.get('artworkUrl100', 'https://via.placeholder.com/100')
        
        if not feed_url:
            continue
            
        st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
        col_img, col_info = st.columns([1, 3])
        with col_img:
            st.image(img_url, use_container_width=True)
        with col_info:
            st.markdown(f"**{title}**")
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                if st.button("Open", key=f"open_{feed_url}"):
                    st.session_state.active_podcast = {"title": title, "feed": feed_url}
                    st.toast("Podcast selected! Go to the 'Player' tab.")
            with subcol2:
                if feed_url in st.session_state.favorites:
                    st.button("Saved", disabled=True, key=f"saved_{feed_url}")
                else:
                    if st.button("⭐
