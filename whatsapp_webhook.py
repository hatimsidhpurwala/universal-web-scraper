import os
import requests
from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from agent import ask
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
user_sessions = {}  # stores chat history per user number

def transcribe_audio(audio_url: str) -> str:
    """Download Twilio audio and transcribe with Groq Whisper."""
    try:
        from groq import Groq
        auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        audio_data = requests.get(audio_url, auth=auth).content
        gc = Groq(api_key=os.getenv("GROQ_API_KEY"))
        transcription = gc.audio.transcriptions.create(
            file=("audio.ogg", audio_data),
            model="whisper-large-v3",
            language="en"
        )
        return transcription.text
    except Exception as e:
        return ""

def extract_image_text(image_url: str) -> str:
    """Download Twilio image and run OCR."""
    try:
        import pytesseract
        from PIL import Image
        import io
        auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        img_data = requests.get(image_url, auth=auth).content
        image = Image.open(io.BytesIO(img_data))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        return ""

@app.post("/webhook", response_class=PlainTextResponse)
async def whatsapp_webhook(request: Request):
    form = await request.form()

    user_number = form.get("From", "")
    body = form.get("Body", "").strip()
    num_media = int(form.get("NumMedia", 0))
    media_type = form.get("MediaContentType0", "")
    media_url = form.get("MediaUrl0", "")

    # --- Handle voice message ---
    if num_media > 0 and "audio" in media_type:
        transcribed = transcribe_audio(media_url)
        if transcribed:
            body = transcribed
        else:
            body = "voice message (could not transcribe)"

    # --- Handle image message ---
    elif num_media > 0 and "image" in media_type:
        ocr_text = extract_image_text(media_url)
        if ocr_text:
            body = ocr_text
        else:
            body = form.get("Body", "").strip() or "image received (no text found)"

    if not body:
        body = "Hello"

    # --- Get answer from RAG pipeline ---
    chat_history = user_sessions.get(user_number, [])
    try:
        result = ask(body, chat_history=chat_history)
        user_sessions[user_number] = result["chat_history"]
        answer = result["answer"]
        if result.get("sources"):
            clean_sources = [s for s in result["sources"] if s not in ["unknown", "uploaded"]]
            if clean_sources:
                answer += f"\n\n📌 Info from: {', '.join(clean_sources)}"
    except Exception as e:
        answer = "Sorry, I couldn't find an answer right now. Please try again or contact us directly."

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)

@app.get("/health")
async def health():
    return {"status": "ok", "message": "WhatsApp RAG bot is running"}