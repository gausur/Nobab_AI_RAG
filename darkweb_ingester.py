#!/usr/bin/env python3
"""
Nobab_AI Dark Web Ingester — Real .onion URLs
সরাসরি Tor নেটওয়ার্ক থেকে ডেটা টেনে এনে JSONL ফাইল হিসেবে সেভ করে।
"""

import requests, os, re, json
from datetime import datetime

SAVE_DIR = "datasets/raw_darkweb"
os.makedirs(SAVE_DIR, exist_ok=True)

BATCH_ID = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
PROXY = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}

# ── বাস্তব .onion সোর্স (Tor চালু থাকলেই কাজ করবে) ──
SOURCES = [
    "http://darkfailllnkf4vf.onion",   # DarkFail — ডার্ক ওয়েব সার্ভিসের লাইভ স্ট্যাটাস
]

def safe_filename(url):
    """URL থেকে নিরাপদ ফাইলের নাম তৈরি করে"""
    name = url.replace("http://", "").replace("https://", "").replace("/", "_")
    name = re.sub(r"[^a-zA-Z0-9_\.]", "_", name)
    return name[:60]

def fetch_and_save(url):
    """একটি .onion URL থেকে HTML ফেচ করে JSONL হিসেবে সংরক্ষণ"""
    try:
        resp = requests.get(url, proxies=PROXY, timeout=30)
        if resp.status_code == 200:
            fname = safe_filename(url)
            jsonl_path = os.path.join(SAVE_DIR, f"{fname}_{BATCH_ID}.jsonl")
            with open(jsonl_path, "w", encoding="utf-8") as f:
                # পুরো HTML টেক্সটকে একক JSONL রেকর্ড হিসেবে সেভ
                f.write(json.dumps({
                    "text": resp.text[:10000],  # প্রথম ১০,০০০ ক্যারেক্টার
                    "source": url,
                    "domain": "darkweb",
                    "timestamp": datetime.utcnow().isoformat()
                }, ensure_ascii=False) + "\n")
            print(f"  ✅ {fname}: {len(resp.text)} chars saved")
            return 1
        else:
            print(f"  ⚠️ HTTP {resp.status_code}: {url}")
            return 0
    except Exception as e:
        print(f"  ❌ Error: {url} — {str(e)[:80]}")
        return 0

def main():
    print(f"🌐 Dark Web Ingester started @ {datetime.utcnow()}")
    total = 0
    for url in SOURCES:
        total += fetch_and_save(url)
    print(f"🎉 Done! {total} sources fetched → {SAVE_DIR}")

if __name__ == "__main__":
    main()
