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
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
if "favorites" not in st.session_state: st.session_state.favorites = {}
if "active_podcast" not in st.session_state: st.session_state.active_podcast = None
if "search_results" not in st.session_state: st.session_state.search_results = []
if "messages" not in st.session_state: st.session_state.messages = []

# --- UI & CSS ---
st.set_page_config(page_title="PodBrief", layout="centered")
bg_color = "#121212" if st.session_state.dark_mode else "#F4F7F9"
card_bg = "#1E1E1E" if st.session_state.dark_mode else "#FFFFFF"
text_color = "#E0E0E0" if st.session_state.dark_mode else "#2C3E50"
accent_color = "#6200EE"

st.markdown(f"""
    <style>
        .main .block-container {{ max-width: 500px !important; padding: 1rem !important; }}
        [data-testid="stRadio"] {{ margin-bottom: 10px !important; }}
        .mobile-card {{ background-color: {card_bg}; border-radius: 20px; padding: 15px; margin-bottom: 15px; border: 1px solid #E1E8ED; }}
        .stButton>button {{ width: 100%; border-radius: 12px; border: none; background: {accent_color}; color: white; padding: 10px; font-weight: 600; }}
        h1, h3 {{ color: {text_color}; margin-top: 0px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_title, col_toggle = st.columns([0.8, 0.2])
with col_title: st.title("🎙️ PodBrief")
with col_toggle:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

nav = st.radio("Navigation", ["🔍 Discover", "⭐ Favorites", "🎧 Player"], horizontal=True, label_visibility="collapsed")

# --- TAB 1: DISCOVER ---
if nav == "🔍 Discover":
    st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
    st.markdown("### Search Directory")
    query = st.text_input("Search", placeholder="e.g. Fantasy Football", label_visibility="collapsed")
    if st.button("Query Database"):
        with st.spinner("Searching..."):
            resp = requests.get(f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&media=podcast&limit=10")
            if resp.status_code == 200: st.session_state.search_results = resp.json().get('results', [])
    st.markdown('</div>', unsafe_allow_html=True)
    
    for pod in st.session_state.search_results:
        st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
        st.write(f"**{pod.get('collectionName')}**")
        if st.button("🎧 Open Show", key=f"open_{pod.get('feedUrl')}"):
            st.session_state.active_podcast = {"title": pod.get('collectionName'), "feed": pod.get('feedUrl')}
            st.toast("Podcast selected!")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: FAVORITES ---
elif nav == "⭐ Favorites":
    for feed_url, data in st.session_state.favorites.items():
        st.markdown(f'<div class="mobile-card">**{data["title"]}**</div>', unsafe_allow_html=True)

# --- TAB 3: PLAYER ---
elif nav == "🎧 Player":
    if not st.session_state.active_podcast:
        st.info("Pick a show from Discover first.")
    else:
        st.write(f"### Now Playing: {st.session_state.active_podcast['title']}")
        # [Add your episode processing logic here]
        if 'uploaded_file' in st.session_state:
            while True:
                file_info = client.files.get(name=st.session_state['uploaded_file'].name)
                if "ACTIVE" in str(file_info.state): break
                time.sleep(15) 
            
            if prompt := st.chat_input("Ask a question about this episode..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                with st.chat_message("assistant"):
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=[st.session_state['uploaded_file'], prompt]
                    )
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
