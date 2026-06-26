import os
import feedparser
import requests
import streamlit as st
from google import genai
import urllib.parse

# Setup Gemini Client
client = genai.Client()

# --- STATE MANAGEMENT ---
# Initialize session variables so the app remembers things between clicks
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "favorites" not in st.session_state:
    st.session_state.favorites = {} # Format: {feedUrl: {"title": title, "img": url}}
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
        .main .block-container {{
            max-width: 460px !important; padding: 1rem !important; background-color: {bg_color}; color: {text_color};
        }}
        .stApp {{ background-color: {bg_color}; }}
        .mobile-card {{
            background-color: {card_bg}; border: 1px solid {border_color}; border-radius: 16px;
            padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        .stButton>button {{
            width: 100% !important; border-radius: 24px !important; border: none !important;
            background-color: {accent_color} !important; color: white !important; font-weight: 600 !important;
            transition: all 0.2s ease;
        }}
        .stTextInput>div>div>input, .stSelectbox>div>div>div {{
            border-radius: 12px !important; background-color: {card_bg} !important; color: {text_color} !important;
        }}
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
# A horizontal radio button group acting like an app tab bar
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

    # Render Search Results
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
                    if st.button("⭐ Save", key=f"fav_{feed_url}"):
                        st.session_state.favorites[feed_url] = {"title": title, "img": img_url}
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: FAVORITES ---
elif nav == "⭐ Favorites":
    if not st.session_state.favorites:
        st.info("You haven't saved any podcasts yet. Go to Discover to find some!")
        
    for feed_url, data in list(st.session_state.favorites.items()):
        st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
        col_img, col_info = st.columns([1, 3])
        with col_img:
            st.image(data['img'], use_container_width=True)
        with col_info:
            st.markdown(f"**{data['title']}**")
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                if st.button("Open", key=f"open_fav_{feed_url}"):
                    st.session_state.active_podcast = {"title": data['title'], "feed": feed_url}
                    st.toast("Podcast selected! Go to the 'Player' tab.")
            with subcol2:
                if st.button("Remove", key=f"rem_{feed_url}"):
                    del st.session_state.favorites[feed_url]
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: PLAYER / SUMMARIZER ---
elif nav == "🎧 Player":
    if not st.session_state.active_podcast:
        st.info("No podcast selected. Go to Discover or Favorites to pick one.")
    else:
        title = st.session_state.active_podcast['title']
        feed_url = st.session_state.active_podcast['feed']
        
        st.markdown(f"### {title}")
        
        # Parse RSS Feed for episodes
        with st.spinner("Fetching latest episodes..."):
            parsed_feed = feedparser.parse(feed_url)
            episodes = {}
            for entry in parsed_feed.entries:
                audio = next((link.href for link in entry.links if 'audio' in link.type), None)
                if audio:
                    episodes[entry.title] = audio
        
        if not episodes:
            st.error("Could not find any playable audio in this feed.")
        else:
            st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
            # Create a dropdown mapping episode titles to URLs
            selected_ep_title = st.selectbox("Select an Episode:", list(episodes.keys()))
            selected_audio_url = episodes[selected_ep_title]
            
            if st.button("Process & Summarize"):
                with st.spinner("Downloading and uploading to Gemini..."):
                    # Clear old summaries
                    st.session_state.pop('base_summaries', None)
                    st.session_state.pop('detailed_summary', None)
                    
                    filename = "active_episode.mp3"
                    r = requests.get(selected_audio_url, stream=True)
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            
                    uploaded_file = client.files.upload(file=filename)
                    st.session_state['uploaded_file'] = uploaded_file
                    
                    if os.path.exists(filename):
                        os.remove(filename)
                        
                    st.session_state['episode_title'] = selected_ep_title
                    st.success("Ready for analysis!")
            st.markdown('</div>', unsafe_allow_html=True)

        # Output Generation Logic (Same as before)
        if 'uploaded_file' in st.session_state and st.session_state.get('episode_title') == selected_ep_title:
            
            if 'base_summaries' not in st.session_state:
                with st.spinner("Analyzing transcript..."):
                    base_prompt = """
                    Analyze the provided podcast audio file and generate two distinct outputs. 
                    Format your response clearly separating them with the tags [ULTRA_SHORT] and [CONCISE_5PERCENT].

                    [ULTRA_SHORT]
                    Provide a very short 1-2 paragraph overview of the entire episode, followed immediately by 3-5 high-level bullet points capturing the overarching themes.

                    [CONCISE_5PERCENT]
                    Provide a condensed set of written notes capturing the core message and key takeaways. Target a length of roughly 600 words (which takes approximately 3 minutes to read at an average pace). Avoid fluff; prioritize dense, actionable insights.
                    """
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[base_prompt, st.session_state['uploaded_file']]
                    )
                    st.session_state['base_summaries'] = response.text

            raw_text = st.session_state['base_summaries']
            ultra_short = raw_text.split("[CONCISE_5PERCENT]")[0].replace("[ULTRA_SHORT]", "").strip()
            concise_notes = raw_text.split("[CONCISE_5PERCENT]")[-1].strip()

            st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
            st.markdown("#### ⚡ Quick Overview")
            st.markdown(ultra_short)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
            st.markdown("#### ⏱️ Concise Notes (~3 Min Read)")
            st.markdown(concise_notes)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="mobile-card">', unsafe_allow_html=True)
            st.markdown("#### 🔍 Deep Dive Breakdown")
            if st.button("Generate 15% Chronological Summary"):
                with st.spinner("Analyzing structural breakdown..."):
                    detailed_prompt = """
                    Analyze the provided podcast audio file and generate a highly detailed summary.
                    Target an overall length of roughly 15% of the total metadata volume (approximately 1,500 to 1,800 words for a 60-minute show).
                    
                    Requirements:
                    1. Organize the summary chronologically as it unfolds in the audio.
                    2. Divide the text into logical structural sections using clear headers based on the concepts, subjects, or subjects addressed.
                    3. Provide deep-dive bullet points under each concept section explaining the arguments, data points, or ideas presented.
                    """
                    detailed_response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[detailed_prompt, st.session_state['uploaded_file']]
                    )
                    st.session_state['detailed_summary'] = detailed_response.text

            if 'detailed_summary' in st.session_state:
                st.markdown(st.session_state['detailed_summary'])
            st.markdown('</div>', unsafe_allow_html=True)
