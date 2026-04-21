# gemini_test.py
import os
import google.generativeai as genai   # <-- correct import (still works)

# -------------------------------------------------
# 1️⃣ Load the API key from the environment
# -------------------------------------------------
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY not set – check your PowerShell env.")
print("✅ API key loaded")

# -------------------------------------------------
# 2️⃣ Configure the client
# -------------------------------------------------
genai.configure(api_key=api_key)

# -------------------------------------------------
# 3️⃣ Pick the image‑capable model you saw in list_models.py
# -------------------------------------------------
model_name = "gemini-2.5-flash"          # <-- change if you prefer a different one
model = genai.GenerativeModel(model_name)

# -------------------------------------------------
# 4️⃣ Very tiny prompt – just to prove the call works
# -------------------------------------------------
response = model.generate_content("Return only the word \"hello\".")
print("Gemini response:", response.text.strip())
