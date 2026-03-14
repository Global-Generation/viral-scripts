FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir openai-whisper && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download Whisper base model during build
RUN python -c "import whisper; whisper.load_model('base')"

COPY . .

RUN mkdir -p downloads

EXPOSE 8070

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8070"]
