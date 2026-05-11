#!/usr/bin/env python3
"""Nobab_AI Dark Web Ingester — Real .onion URLs"""
import requests, json, os, time
from datetime import datetime

SAVE_DIR = "datasets/raw_darkweb"
os.makedirs(SAVE_DIR, exist_ok=True)
BATCH = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
PROXY = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}

SOURCES = [
    "http://darkfailllnkf4vf.onion",   # DarkFail — ডার্ক ওয়েবের লাইভ স্ট্যাটাস
]

for url in SOURCES:
    try:
        resp = requests.get(url, proxies=PROXY, timeout=30)
        if resp.status_code == 200:
            fname = url.replace("http://","").replace("https://","").replace("/","_")[:50]
            path = f"{SAVE_DIR}/{fname}_{BATCH}.html"
            with open(path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"✅ ডাউনলোড সফল: {fname}")
        else:
            print(f"⚠️ HTTP {resp.status_code}: {url}")
    except Exception as e:
        print(f"❌ এরর: {url} — {str(e)[:80]}")
