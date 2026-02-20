FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "if [ \"${PRELOAD_WHISPER_AT_STARTUP:-0}\" = \"1\" ]; then python -c \"import os; from faster_whisper import WhisperModel; WhisperModel(os.getenv('WHISPER_MODEL', 'tiny.en'), device='cpu', compute_type='int8')\"; fi; exec uvicorn app:app --host 0.0.0.0 --port 10000"]
