import requests, json, os, time
from datetime import datetime

SAVE_DIR = "datasets/raw_darkweb"
os.makedirs(SAVE_DIR, exist_ok=True)
BATCH = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
PROXY = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}

SOURCES = [
    "http://darkfailenbsdla5mal2mxn2uz66od5vtzd5qozslagrfzachha3f3id.onion",
    "http://breachforums... (তোর জানা অনিয়ন লিংক)",
]

for url in SOURCES:
    try:
        resp = requests.get(url, proxies=PROXY, timeout=30)
        if resp.status_code == 200:
            fname = url.replace("http://","").replace("https://","").replace("/","_")[:50]
            with open(f"{SAVE_DIR}/{fname}_{BATCH}.html", "w") as f:
                f.write(resp.text)
    except:
        pass
