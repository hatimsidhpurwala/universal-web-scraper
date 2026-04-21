# list_models.py
import os
import google.generativeai as genai   # <-- use the proper module

# -------------------------------------------------
# 1️⃣ Load the API key from the environment
# -------------------------------------------------
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY not set – make sure you set it in PowerShell.")
print("✅ API key loaded")

# -------------------------------------------------
# 2️⃣ Configure the Gemini client
# -------------------------------------------------
genai.configure(api_key=api_key)   # <-- this works now

# -------------------------------------------------
# 3️⃣ List the models that are available to your project
# -------------------------------------------------
models = genai.list_models()
print("\n=== AVAILABLE GEMINI MODELS ===")
for m in models:
    # m.name looks like "models/gemini-1.5-flash-001"
    print(f"- {m.name}")
