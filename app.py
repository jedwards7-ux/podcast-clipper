import os
import time
import tempfile
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
if "current_summary" not in st.session_state: st.session_state.current_summary = ""
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "uploaded_file_ref" not in st.session_state: st.session_state.uploaded_file_ref = None

# --- UI & CSS LAYOUT POLISH ---
st.set_page_config(page_title="PodBrief", layout="centered")

bg_color = "#121212" if st.session_state.dark_mode else "#F4F7F9"
card_bg = "#1E1E1E" if st.session_state.dark_mode else "#FFFFFF"
text_color = "#E0E0E0" if st.session_state.dark_mode else "#2C3E50"
accent_color = "#6200EE"

st.markdown(f"""
    <style>
        .main .block-container {{ max-width: 500px !important; padding: 1rem !important; }}
        [data-testid="stRadio"] div[role="radiogroup"] {{ margin-bottom: 0px !important; padding: 0px !important; }}
        div.stRadio > div {{ margin-top: -10px !important; }}
        .mobile-card {{ background-color: {card_bg}; border-radius: 16px; padding: 16px; margin-bottom: 12px; border: 1px solid #E1E8ED; }}
        .stButton>button {{ width: 100%; border-radius: 10px; border: none; background: {accent_color}; color: white; padding: 8px; font-weight: 600; }}
        h1, h2, h3 {{ color: {text_color}; margin-top: 0px !important; margin-bottom: 8px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_title, col_toggle = st.columns([0.8, 0.2])
with col_title: 
    st.title("🎙️ PodBrief")
with col_toggle:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

nav = st.radio("Navigation", ["🔍 Discover", "⭐ Favorites", "🎧 Player"], horizontal=True, label_visibility="collapsed")

# --- TAB 1: DISCOVER ---
if nav == "🔍 Discover":
    st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
    st.markdown("### Search Directory")
    query = st.text_input("Search Input", placeholder="e.g. Fantasy Football", label_visibility="collapsed")
    if st.button("Query Database"):
        with st.spinner("Searching..."):
            safe_query = urllib.parse.quote(query)
            resp = requests.get(f"https://itunes.apple.com/search?term={safe_query}&media=podcast&limit=10")
            if resp.status_code == 200: 
                st.session_state.search_results = resp.json().get('results', [])
    st.markdown('</div>', unsafe_allow_html=True)
    
    for pod in st.session_state.search_results:
        st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
        st.write(f"**{pod.get('collectionName')}**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎧 Open Show", key=f"open_{pod.get('feedUrl')}"):
                st.session_state.active_podcast = {"title": pod.get('collectionName'), "feed": pod.get('feedUrl')}
                st.session_state.current_summary = ""
                st.session_state.transcript = ""
                st.session_state.messages = []
                st.session_state.uploaded_file_ref = None
                st.rerun()
        with col2:
            if st.button("⭐ Save Show", key=f"fav_{pod.get('feedUrl')}"):
                st.session_state.favorites[pod.get('feedUrl')] = {"title": pod.get('collectionName')}
                st.toast("Saved to Favorites!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: FAVORITES ---
elif nav == "⭐ Favorites":
    if not st.session_state.favorites:
        st.info("No saved shows found in this session.")
    else:
        for feed_url, data in st.session_state.favorites.items():
            st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
            st.write(f"**{data['title']}**")
            if st.button("🎧 Open Show", key=f"fav_open_{feed_url}"):
                st.session_state.active_podcast = {"title": data['title'], "feed": feed_url}
                st.session_state.current_summary = ""
                st.session_state.transcript = ""
                st.session_state.messages = []
                st.session_state.uploaded_file_ref = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: PLAYER & INTERACTIVE CHAT ---
elif nav == "🎧 Player":
    if not st.session_state.active_podcast:
        st.info("Pick a show from Discover or Favorites first.")
    else:
        st.markdown(f"### Now Playing: {st.session_state.active_podcast['title']}")
        
        with st.spinner("Fetching latest episodes..."):
            feed = feedparser.parse(st.session_state.active_podcast['feed'])
            
        if not feed.entries:
            st.error("Unable to parse RSS feed elements.")
        else:
            episodes = {ep.title: ep for ep in feed.entries[:10]}
            selected_title = st.selectbox("Select Episode", list(episodes.keys()), label_visibility="collapsed")
            selected_ep = episodes[selected_title]
            
            audio_url = None
            if hasattr(selected_ep, 'enclosures') and selected_ep.enclosures:
                audio_url = selected_ep.enclosures[0].href
                
            if audio_url:
                if st.button("🎙️ Process & Summarize Episode"):
                    st.session_state.messages = [] 
                    st.session_state.transcript = ""
                    
                    with st.spinner("Downloading audio stream..."):
                        r = requests.get(audio_url, stream=True)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                if chunk: tmp.write(chunk)
                            tmp_path = tmp.name
                            
                    with st.spinner("Uploading to Google File API..."):
                        uploaded_file = client.files.upload(file=tmp_path)
                        st.session_state.uploaded_file_ref = uploaded_file
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                            
                    status_area = st.empty()
                    while True:
                        file_info = client.files.get(name=st.session_state.uploaded_file_ref.name)
                        status_area.info(f"Processing audio file status: {file_info.state}")
                        if "ACTIVE" in str(file_info.state):
                            break
                        elif "FAILED" in str(file_info.state):
                            status_area.empty()
                            st.error("Google's servers failed to process this specific audio track.")
                            st.stop()
                        time.sleep(15)
                    status_area.empty()
                    
                    with st.spinner("Transcribing and Summarizing content..."):
                        try:
                            # 1. Fetch the absolute full text transcript first
                            tx_response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[st.session_state.uploaded_file_ref, "Provide a word-for-word complete transcript or a detailed textual log of everything spoken in this audio."]
                            )
                            st.session_state.transcript = tx_response.text
                            
                            # 2. Use that transcript to build the high-level summary immediately
                            sum_response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[f"Based entirely on the following podcast transcript, provide a comprehensive summary:\n\n{st.session_state.transcript}"]
                            )
                            st.session_state.current_summary = sum_response.text
                            
                            # Clean up file reference from API since we now have the text cached locally
                            client.files.delete(name=st.session_state.uploaded_file_ref.name)
                            st.session_state.uploaded_file_ref = None
                            
                        except Exception as e:
                            st.error(f"Google API Server Error: {e}")
            else:
                st.error("No enclosure audio format found for this entry.")

        # Display analysis results and text-based chat assistant
        if st.session_state.current_summary:
            st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
            st.markdown("### 📝 Episode Summary")
            st.markdown(st.session_state.current_summary)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("### 💬 Podcast Assistant")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): 
                    st.markdown(msg["content"])
            
            if prompt := st.chat_input("Ask a question about this episode..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): 
                    st.markdown(prompt)
                    
                with st.chat_message("assistant"):
                    with st.spinner("Reading transcript cache..."):
                        try:
                            # Pure text-based reasoning now. Snappy and free-tier safe.
                            chat_context = f"You are analyzing a podcast episode. Use the text transcript below to answer the user's prompt.\n\n[TRANSCRIPT]\n{st.session_state.transcript}\n\n[PROMPT]\n{prompt}"
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[chat_context]
                            )
                            st.markdown(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                        except Exception as e:
                            st.error(f"API Error during chat execution: {e}")
