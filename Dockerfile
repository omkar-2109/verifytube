FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY app.py .
COPY backend.py .
COPY cookies.txt /app/cookies.txt .

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
