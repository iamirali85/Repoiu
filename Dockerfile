# Dockerfile — base image, install ffmpeg and build tools for pyworld, install python deps
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system deps: ffmpeg, libsndfile, build tools (for pyworld), cmake
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      libsndfile1 \
      build-essential \
      cmake \
      git \
      wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy app files
COPY . /app

# Expose no port (bot uses long-polling). If you switch to webhook, expose 443/80 as needed.
CMD ["python", "bot.py"]
