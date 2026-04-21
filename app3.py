# --------------------------------------------------------------
#  IMPORTS  (keep your scraper‑specific imports at the top)
# --------------------------------------------------------------
import streamlit as st
from streamlit_tags import st_tags_sidebar
from streamlit_lottie import st_lottie
import pandas as pd, json, io, os, time, logging
from datetime import datetime
from PIL import Image
# Replace any line that says:
# import google.generativeai as genai   # (old or duplicated)
import os
from dotenv import load_dotenv
load_dotenv(override=True)  # reads .env in the current working dir
# Use the same import that works:
#import google.generativeai as genai

# Your own modules – leave as‑is
from scraper import (
    fetch_html_selenium, save_raw_data, format_data,
    save_formatted_data, calculate_price,
    html_to_markdown_with_readability,
    create_dynamic_listing_model, create_listings_container_model
)
from assets import PRICING

#def _get_gemini_model():
#    api_key = os.getenv("GOOGLE_API_KEY")
#    if not api_key:
#        logger.warning("GOOGLE_API_KEY not set – Gemini disabled, OCR only.")
#        return None
#
#    genai.configure(api_key=api_key)
#    try:
#        return genai.GenerativeModel("gemini-2.5-flash")
#   except Exception as e:
#        logger.warning(f"Gemini init failed: {e} – using OCR only.")
#        return None

# --------------------------------------------------------------
#  GLOBAL SETTINGS / LOGGING
# --------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
#  STREAMLIT PAGE CONFIG
# --------------------------------------------------------------
st.set_page_config(
    page_title="Smart Web Scraper",
    page_icon="🦑",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Hide Streamlit default UI
st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

st.header(":red[Smart] :green[Web Scraper] 🦑", divider='rainbow')
st.caption("Effortless Data Extraction, Powered by Generative AI")

# --------------------------------------------------------------
#  1️⃣ VOICE INPUT COMPONENT
# --------------------------------------------------------------
def voice_input_component():
    audio_file = st.sidebar.file_uploader(
        "🎤 Upload Voice (mp3/wav/m4a)",
        type=["mp3", "wav", "m4a", "webm"],
        key="voice_upload"
    )
    if audio_file:
        with st.spinner("🎤 Transcribing voice..."):
            try:
                from groq import Groq
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                transcription = client.audio.transcriptions.create(
                    file=(audio_file.name, audio_file.read()),
                    model="whisper-large-v3",
                    language="en"
                )
                text = transcription.text
                fields = [
                    f.strip() for f in 
                    text.replace(" and ", ",").split(",") 
                    if f.strip()
                ]
                st.sidebar.success(f"✅ Heard: {text}")
                st.session_state['voice_fields'] = fields
            except Exception as e:
                st.sidebar.error(f"❌ Voice error: {e}")
                
                
# --------------------------------------------------------------
# 2️⃣ IMAGE INPUT COMPONENT (OCR + Gemini fallback)
# --------------------------------------------------------------
#def _configure_gemini():
#    """Configure Gemini once and return the model object."""
#    api_key = os.getenv("GOOGLE_API_KEY")
#    if not api_key:
#        st.sidebar.error("❌ Missing GOOGLE_API_KEY env var – Gemini disabled.")
#        return None
#    genai.configure(api_key=api_key)
#    # Use a model with a free‑tier quota (1.5‑flash) – more generous than 2.0‑flash
#    return genai.GenerativeModel("gemini-1.5-flash")
#

#def _gemini_image_fields(image: Image.Image) -> list | None:
#    """Ask Gemini to list fields from the screenshot. Returns None on any quota error."""
#    model = _configure_gemini()
#    if not model:
#        return None
#    try:
#        response = model.generate_content(
#            [
#                "Given this screenshot of a product page, list the data fields you would extract for a scraper. Return ONLY a comma‑separated list, nothing else.",
#                image,
#            ]
#        )
#        if response.text:
#            return [f.strip() for f in response.text.split(",") if f.strip()]
#    except Exception as exc:
#        # Detect quota‑exhausted errors
#        if "quota" in str(exc).lower() or "resource exhausted" in str(exc).lower():
#            st.sidebar.warning("⚠️ Gemini quota exhausted – falling back to local OCR.")
#            return None
#        else:
##            st.sidebar.error(f"❌ Gemini error: {exc}")
#            logger.exception("Gemini call failed")
#            return None


def _ocr_image_text(image: Image.Image) -> str:
    """
    Local OCR using pytesseract, returns a single text string.
    """
    try:
        import pytesseract
        import numpy as np
        import cv2

        if os.name == "nt":
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        img = np.array(image.convert("RGB"))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 3)
        _, thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(thresh, lang="eng", config=config)

        text = text.strip()
        st.sidebar.text_area("📝 Raw OCR text", value=text, height=150)
        return text

    except Exception as exc:
        st.sidebar.warning(f"⚠️ OCR failed ({exc}) – using empty string.")
        logger.exception("OCR error")
        return ""

def image_to_fields(image_file):
    """
    Use OCR to get a single text string from the screenshot
    and store it for later use.
    """
    import io
    image_bytes = image_file.read()
    image = Image.open(io.BytesIO(image_bytes))

    st.sidebar.image(image, caption="Uploaded screenshot", use_column_width=True)
    st.sidebar.info("🔍 Running local OCR on image…")

    text = _ocr_image_text(image)

    # Save full sentence/string in session_state
    st.session_state["image_query"] = text

    # If you still want to auto-suggest field names for scraping,
    # derive them here from the string (optional).
    
    return []

# --------------------------------------------------------------
# 3️⃣ UI – SIDEBAR SETTINGS
# --------------------------------------------------------------
st.sidebar.title("Web Scraper Settings")
model_selection = st.sidebar.selectbox(
    "Select Model for LLM extraction", list(PRICING.keys()), index=0
)
url_input = st.sidebar.text_input("Enter URL to scrape")

# ---- 3️⃣‑A️⃣ Manual tag entry (still useful) ----
tags_placeholder = st.sidebar.empty()
manual_tags = st_tags_sidebar(
    label="Enter Fields to Extract (manual)",
    text="Press Enter to add a tag",
    value=[],
    suggestions=[],
    maxtags=-1,
    key="manual_tags",
)

# ---- 3️⃣‑B️⃣ Voice & Image input columns ----
col_voice, col_image = st.sidebar.columns(2)
with col_voice:
    if st.button("🎤 Voice Input"):
        voice_input_component()

with col_image:
    uploaded_image = st.file_uploader(
        "🖼️ Upload screenshot (optional)",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )
    if uploaded_image:
        with st.spinner("Analyzing image…"):
            img_fields = image_to_fields(uploaded_image)
            if img_fields:
                st.session_state["image_fields"] = img_fields
                st.sidebar.success(f"🖼️ Image fields: {', '.join(img_fields)}")

# --------------------------------------------------------------
# 4️⃣ MERGE ALL FIELD sources into ONE LIST
# --------------------------------------------------------------
def _collect_all_fields() -> list:
    """Collect voice, image, and manual tags into a single list (no duplicates)."""
    collected = set()

    if "voice_fields" in st.session_state:
        collected.update(st.session_state["voice_fields"])
    if "image_fields" in st.session_state:
        collected.update(st.session_state["image_fields"])
    if "image_query" in st.session_state:
        query = st.session_state["image_query"]
        if query:                    # ← must be indented inside the if block
            collected.add(query)
    if manual_tags:
        collected.update(manual_tags)

    return list(collected)

# --------------------------------------------------------------
# 5️⃣ SCRAPING LOGIC (unchanged – just uses extracted fields)
# --------------------------------------------------------------
if "extracted_fields" not in st.session_state:
    st.session_state["extracted_fields"] = []

st.session_state["extracted_fields"] = _collect_all_fields()

def perform_scrape():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ✅ REUSE already-crawled markdown if same URL
    cached = st.session_state.get("cached_crawl", {})
    
    if cached.get("url") == url_input and cached.get("markdown"):
        st.sidebar.success("✅ Using cached website data — no re-crawling!")
        markdown = cached["markdown"]
    else:
        from scraper import crawl_site
        st.sidebar.info("🕷️ Crawling website for first time... 1-2 minutes")
        pages_html = crawl_site(url_input, max_pages=20, max_depth=3)
        all_markdown_parts = []
        for url, html in pages_html.items():
            md = html_to_markdown_with_readability(html)
            all_markdown_parts.append(f"\n\n### PAGE: {url}\n\n{md}")
        markdown = "\n".join(all_markdown_parts)
        
        # ✅ Save to session cache
        st.session_state["cached_crawl"] = {
            "url": url_input,
            "markdown": markdown
        }
        save_raw_data(markdown, timestamp)
# --------------------------------------------------------------
# 6️⃣ SCRAPE BUTTON & RESULT DISPLAY
# --------------------------------------------------------------
if "scrape_done" not in st.session_state:
    st.session_state["scrape_done"] = False
# Clear Cache button - standalone, simple
if st.sidebar.button("🗑️ Clear Cache", help="Force re-crawl the website"):
    st.session_state.pop("cached_crawl", None)
    st.sidebar.success("Cache cleared! Next scrape will re-crawl.")

# Scrape button - separate, unchanged
if st.sidebar.button("🚀 Scrape"):
    if not url_input:
        st.sidebar.error("⚠️ Please provide a URL before scraping.")
    else:
        image_query = st.session_state.get("image_query", "").strip()
        fields = st.session_state.get("extracted_fields", [])

        if not image_query and not fields:
            st.sidebar.warning(
                "⚠️ No OCR text, voice fields, or manual fields provided. "
                "The model will use its internal defaults."
            )

        with st.spinner("🕒 Scraping… This may take a moment."):
            st.session_state["results"] = perform_scrape()
            st.session_state["scrape_done"] = True
            st.rerun()
            # --------------------------------------------------------------
# 7️⃣ DISPLAY RESULTS (only after scrape)
# --------------------------------------------------------------
if st.session_state.get("scrape_done"):
    df, formatted_data, markdown, i_tok, o_tok, cost, ts = st.session_state["results"]

    st.success("✅ Scraping completed!")
    st.subheader("📄 Extracted Answer")

    if isinstance(formatted_data, str):
        st.info(formatted_data)
    elif isinstance(formatted_data, dict):
        listings = formatted_data.get("listings", [])
        if listings and isinstance(listings[0], dict):
            for key, value in listings[0].items():
                if value and value.lower() != "not specified":
                    st.info(f"**{key}:** {value}")
                else:
                    st.warning(f"**{key}:** This information was not found on the website.")
        else:
            st.info(str(formatted_data))
    else:
        st.info(str(formatted_data))

    # Token / cost info
    st.sidebar.markdown("## Token Usage")
    st.sidebar.write(f"**Input:** {i_tok}")
    st.sidebar.write(f"**Output:** {o_tok}")
    st.sidebar.write(f"**Cost:** :green-background[${cost:.4f}]")

    # Download buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="Download JSON",
            data=json.dumps(
                formatted_data.dict() if hasattr(formatted_data, "dict") else formatted_data,
                indent=4,
            ),
            file_name=f"{ts}_data.json",
        )
    with col2:
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button(
            label="Download Excel",
            data=buffer.getvalue(),
            file_name=f"{ts}_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col3:
        st.download_button(
            label="Download Markdown",
            data=markdown,
            file_name=f"{ts}_data.md",
        )
        
# 8️⃣ FOOTER / CREDITS
# --------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    🚀 Created by **[HATIM](https://github.com/hatim)**  
    Powered by **Google Gemini**, **Streamlit**, **Selenium**, **Pydantic**
    """
)

