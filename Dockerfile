FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pytesseract and opencv
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Start the app
CMD uvicorn whatsapp_webhook:app --host 0.0.0.0 --port $PORT