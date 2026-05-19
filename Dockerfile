FROM python:3.9-slim

# সার্ভারে ক্রোম ব্রাউজার এবং ভার্চুয়াল ডিসপ্লে ড্রাইভার ইনস্টল করা
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# এক্সভিএফবি কন্টেইনার স্ক্রিন অন করে পাইথন রান করা
CMD Xvfb :99 -screen 0 1920x1080x24 & export DISPLAY=:99 && python scanner.py
