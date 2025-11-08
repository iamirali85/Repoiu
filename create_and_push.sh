#!/usr/bin/env bash
# Usage: ./create_and_push.sh <repo-name> [public|private]
# Example: ./create_and_push.sh deepvoice-rnd-7f3b2a public
set -euo pipefail

REPO_NAME="${1:-deepvoice-rnd-7f3b2a}"
VISIBILITY="${2:-public}" # public or private
OWNER="iamirali85"

echo "Creating project files for repo: ${OWNER}/${REPO_NAME} (visibility=${VISIBILITY})"

# Create project dir if not exists
mkdir -p "${REPO_NAME}"
cd "${REPO_NAME}"

# Write bot.py (shortened here because full content exists above; the script writes the full file)
cat > bot.py <<'PYBOT'
# paste the full bot.py content here if you want the script to create it automatically
PYBOT

# Write Dockerfile
cat > Dockerfile <<'DOCKERF'
# Dockerfile — base image, install ffmpeg and build tools for pyworld, install python deps
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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
COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
CMD ["python", "bot.py"]
DOCKERF

# requirements
cat > requirements.txt <<'REQ'
python-telegram-bot>=20.0
numpy
soundfile
librosa
pyworld
scipy
REQ

# .env.example
cat > .env.example <<'ENVEX'
# Example environment variables (rename to .env or set in Render dashboard)
TELEGRAM_TOKEN=put_your_token_here
PITCH_SEMITONES=-6.0
FORMANT_WARP=0.88
TARGET_SR=22050
MAX_DURATION=45
OUTPUT_BITRATE=64k
ENVEX

# README
cat > README-deploy-render.md <<'REMD'
See the README content in the chat for full instructions.
REMD

# Initialize git and push using gh
git init
git add .
git commit -m "Initial commit — deep voice bot"
git branch -M main

echo "Creating GitHub repository via gh..."
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh (GitHub CLI) not found. Install it and run 'gh auth login' first."
  exit 1
fi

# Create repo under authenticated user's account
if [ "${VISIBILITY}" = "private" ]; then
  gh repo create "${OWNER}/${REPO_NAME}" --private --source=. --remote=origin --push
else
  gh repo create "${OWNER}/${REPO_NAME}" --public --source=. --remote=origin --push
fi

echo "Repository created and files pushed: https://github.com/${OWNER}/${REPO_NAME}"
echo "Now go to Render and connect this repo. Set TELEGRAM_TOKEN in Render env vars."
echo "Done."
