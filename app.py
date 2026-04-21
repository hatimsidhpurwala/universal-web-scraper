import streamlit as st
import pandas as pd, json, io, os, time, logging
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv
load_dotenv(override=True)

from scraper import (
    fetch_html_selenium, save_raw_data, format_data,
    save_formatted_data, calculate_price,
    html_to_markdown_with_readability,
    create_dynamic_listing_model, create_listings_container_model
)
from assets import PRICING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Smart Web Scraper",
    page_icon="🦑",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("<style>#MainMenu, footer, header {visibility: hidden;}</style>", unsafe_allow_html=True)
st.header(":red[Smart] :green[Web Scraper] 🦑", divider='rainbow')
st.caption("Effortless Data Extraction, Powered by Generative AI")

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
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(thresh, lang="eng", config=config)
        text = text.strip()
        st.sidebar.text_area("📝 Raw OCR text", value=text, height=150)
        return text

    except Exception as exc:
        st.sidebar.warning(f"⚠️ OCR failed ({exc}) – using empty string.")
        logger.exception("OCR error")
        return ""

tab1, tab2 = st.tabs(["🕷️ Tab 1: Scrape & Save", "💬 Tab 2: Ask Questions"])
# ══════════════════════════════════════════════════════════════
# TAB 1 — SCRAPE & SAVE
# ══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("🕷️ Scrape Website & Save Data")
    st.info("Enter a URL and scrape the FULL website. All pages will be saved to a file you can download and use in Tab 2.")

    url_input = st.text_input("🌐 Enter URL to scrape", placeholder="https://example.com")

    col_a, col_b = st.columns(2)
    with col_a:
        max_pages = st.slider("Max pages to crawl", 5, 100, 30)
    with col_b:
        max_depth = st.slider("Crawl depth", 1, 6, 3)

    if st.button("🚀 Scrape Full Website", use_container_width=True):
        if not url_input:
            st.error("⚠️ Please enter a URL.")
        else:
            from scraper import crawl_site
            progress = st.progress(0, text="Starting crawl...")
            status = st.empty()

            with st.spinner(f"🕷️ Crawling up to {max_pages} pages..."):
                pages_html = crawl_site(url_input, max_pages=max_pages, max_depth=max_depth)

            progress.progress(50, text="Converting to markdown...")
            all_parts = []
            for i, (url, html) in enumerate(pages_html.items()):
                md = html_to_markdown_with_readability(html)
                all_parts.append(f"\n\n### PAGE: {url}\n\n{md}")
                status.text(f"Processing page {i+1}/{len(pages_html)}: {url}")

            combined_markdown = "\n".join(all_parts)
            progress.progress(90, text="Saving data...")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_raw_data(combined_markdown, timestamp)

            # Store in session
            st.session_state["scraped_markdown"] = combined_markdown
            st.session_state["scraped_url"] = url_input
            st.session_state["scrape_timestamp"] = timestamp

            progress.progress(100, text="Done!")
            st.success(f"✅ Scraped {len(pages_html)} pages successfully!")
            # ADD after "st.success(f"✅ Scraped {len(pages_html)} pages...")"
            with st.spinner("🧠 Building vector index..."):
                from scraper import ingest_site_to_qdrant
                chunk_count = ingest_site_to_qdrant(pages_html)
                st.success(f"✅ Indexed {chunk_count} chunks into Qdrant")
                st.session_state["qdrant_ready"] = True
            st.info(f"📁 Raw data saved to: output/rawData_{timestamp}.md")

            # Download button
            st.download_button(
                label="⬇️ Download Scraped Data (.md)",
                data=combined_markdown,
                file_name=f"scraped_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )

# ══════════════════════════════════════════════════════════════
# TAB 2 — ASK QUESTIONS
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("💬 Ask Questions About Scraped Data")

    data_source = st.radio(
        "Choose data source:",
        ["Use data from Tab 1 (already scraped)", "Upload a saved .md file"],
        horizontal=True
    )

    context_markdown = ""

    if data_source == "Use data from Tab 1 (already scraped)":
        if "scraped_markdown" in st.session_state:
            st.success(f"✅ Using scraped data from: {st.session_state.get('scraped_url', 'unknown')}")
            context_markdown = st.session_state["scraped_markdown"]
        else:
            st.warning("⚠️ No scraped data found. Go to Tab 1 and scrape a website first.")

    else:
        uploaded_file = st.file_uploader("Upload .md or .txt file", type=["md", "txt"])
        if uploaded_file:
            context_markdown = uploaded_file.read().decode("utf-8")
            st.success(f"✅ File loaded: {uploaded_file.name} ({len(context_markdown):,} characters)")

            if not st.session_state.get("qdrant_ready"):
                with st.spinner("🧠 Building vector index from uploaded file..."):
                    try:
                        from chunker import chunk_markdown
                        from embedder import embed_chunks
                        from vector_store import store_chunks, clear_collection
                        from cleaner import deduplicate_chunks, normalize_text

                        clear_collection()
                        cleaned = normalize_text(context_markdown)
                        chunks = chunk_markdown(cleaned, source_url=uploaded_file.name)
                        chunks = deduplicate_chunks(chunks)
                        chunks = embed_chunks(chunks)
                        count = store_chunks(chunks)
                        st.session_state["qdrant_ready"] = True
                        st.success(f"✅ Indexed {count} chunks — ready to answer questions")
                    except Exception as e:
                        st.error(f"❌ Indexing failed: {e}")
       
    # ── Model + Voice/Image input ──
    if context_markdown:
        st.divider()

        col_model, col_input = st.columns([2, 1])
        with col_model:
            model_selection = st.selectbox("🤖 Select Model", options=list(PRICING.keys()), index=0)

        # ── Voice input ──
        with col_input:
            st.markdown("**🎤 Voice Input**")
            audio_value = st.audio_input("Click mic to record")
            if audio_value:
                with st.spinner("🎤 Transcribing..."):
                    try:
                        from groq import Groq
                        gc = Groq(api_key=os.getenv("GROQ_API_KEY"))
                        transcription = gc.audio.transcriptions.create(
                            file=("audio.wav", audio_value.read()),
                            model="whisper-large-v3",
                            language="en"
                        )
                        st.session_state["voice_question"] = transcription.text
                        st.success(f"🎤 Heard: {transcription.text}")
                    except Exception as e:
                        st.error(f"Voice error: {e}")

        # ── Image input ──
        img_file = st.file_uploader("🖼️ Upload image (optional)", type=["png","jpg","jpeg"], key="img_tab2")
        if img_file:
            with st.spinner("Reading image..."):
                ocr_text = _ocr_image_text(Image.open(img_file))
                if ocr_text:
                    st.session_state["image_question"] = ocr_text
                    st.success(f"🖼️ OCR: {ocr_text[:100]}...")

        # ── Question input ──
        st.divider()
        default_q = (
            st.session_state.get("voice_question") or
            st.session_state.get("image_question") or ""
        )
        question = st.text_area(
            "❓ Ask your question:",
            value=default_q,
            placeholder="e.g. What CCTV brands do they install?",
            height=100
        )

        if st.button("💬 Get Answer", use_container_width=True):
            if not question:
                st.error("Please enter a question.")
            else:
                history = st.session_state.get("qa_history", [])
                if history and history[-1]["question"] == question:
                    st.warning("⚠️ This question was already answered above.")
                else:
                    with st.spinner("🤖 Thinking..."):
                        try:
                            from agent import ask
                            chat_history = st.session_state.get("chat_history", [])
                            result = ask(question, chat_history=chat_history)
                            st.session_state["chat_history"] = result["chat_history"]
                            st.session_state.setdefault("qa_history", [])
                            st.session_state["qa_history"].append({
                                "question": question,
                                "answer": result["answer"],
                                "sources": result["sources"]
                            })
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

        # ── Show Q&A history ──
        if st.session_state.get("qa_history"):
            st.divider()
            st.subheader("💬 Conversation History")
            for i, qa in enumerate(reversed(st.session_state["qa_history"])):
                with st.expander(f"Q: {qa['question'][:60]}...", expanded=(i==0)):
                    st.markdown(f"**Question:** {qa['question']}")
                    st.info(qa['answer'])
                    if qa.get("sources"):
                        st.caption("Sources: " + " | ".join(qa["sources"]))

            if st.button("🗑️ Clear History"):
                st.session_state["qa_history"] = []
                st.rerun()

# ── Footer ──
st.sidebar.markdown("---")
st.sidebar.markdown("🚀 Created by **HATIM**")