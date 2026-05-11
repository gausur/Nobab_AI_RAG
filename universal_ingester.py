#!/usr/bin/env python3
"""
Nobab_AI Universal Ingester v7.0 — Batch Mode
প্রতি রানে ৩০০-৪০০ সোর্স প্রসেস করে, পরের রানে বাকিগুলো।
"""

import os, json, requests, csv, io, time, chromadb
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from chromadb.utils import embedding_functions

BATCH_SIZE = 350
PROGRESS_FILE = "source_progress.json"
CHROMA_PATH = "./chroma_db"
BATCH_ID = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
HDR = {"User-Agent": "Nobab_AI-Batch/7.0"}

# ChromaDB setup
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
client = chromadb.PersistentClient(path=CHROMA_PATH)

def load_all_sources():
    all_sources = []
    for fname in ["sources1.json", "sources2.json", "sources3.json"]:
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("sources", [])
                all_sources.extend(items)
    return all_sources

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"processed": [], "total_processed": 0}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def get_collection(domain):
    return client.get_or_create_collection(name=f"raw_{domain}_knowledge", embedding_function=ef)

def clean_text(raw):
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 30]
    seen = set()
    unique = []
    for l in lines:
        if l not in seen:
            seen.add(l)
            unique.append(l)
    return "\n".join(unique)

def chunk_text(text):
    chunks = []
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
    for para in paragraphs:
        if len(para) <= 500:
            chunks.append(para)
        else:
            sentences = [s.strip() + "." for s in para.replace("\n", " ").split(".") if s.strip()]
            current = ""
            for s in sentences:
                if len(current) + len(s) <= 500:
                    current += s + " "
                else:
                    if current: chunks.append(current.strip())
                    current = s + " "
            if current: chunks.append(current.strip())
    return chunks

def ingest_source(src):
    name = src.get("name", "unknown")
    url = src.get("url", "")
    domain = src.get("domain", "cyber")
    stype = src.get("type", "html")
    try:
        r = requests.get(url, headers=HDR, timeout=30)
        if r.status_code != 200:
            print(f"  ⚠️ {name}: HTTP {r.status_code}")
            return 0
        raw = r.text[:50000] if stype == "html" else r.content[:50000].decode("utf-8", errors="ignore")
        clean = clean_text(raw)
        chunks = chunk_text(clean)
        if not chunks:
            print(f"  ⚠️ {name}: no valid chunks")
            return 0
        collection = get_collection(domain)
        ids = [f"{name.replace(' ', '_')[:50]}_{i}_{BATCH_ID}" for i in range(len(chunks))]
        metas = [{"source": name, "domain": domain, "chunk": i, "total": len(chunks)} for i in range(len(chunks))]
        for i in range(0, len(chunks), 50):
            collection.add(documents=chunks[i:i+50], ids=ids[i:i+50], metadatas=metas[i:i+50])
        print(f"  ✅ {name}: {len(chunks)} chunks")
        return len(chunks)
    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:100]}")
        return 0

def main():
    print(f"╔══════════════════════════════════════╗")
    print(f"║  Nobab_AI Universal Ingester v7.0  ║")
    print(f"║  Batch Mode — {BATCH_SIZE}/run      ║")
    print(f"╚══════════════════════════════════════╝")
    print(f"📅 {datetime.utcnow()}\n")

    all_sources = load_all_sources()
    progress = load_progress()
    processed_names = set(progress["processed"])

    pending = [s for s in all_sources if s["name"] not in processed_names]
    batch = pending[:BATCH_SIZE]

    print(f"📋 Total: {len(all_sources)} | Already done: {len(processed_names)} | This batch: {len(batch)}\n")

    if not batch:
        print("✅ All sources already processed! Nothing to do.")
        return

    total_chunks = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(ingest_source, s): s for s in batch}
        for f in as_completed(futures):
            src = futures[f]
            try:
                chunks = f.result()
                total_chunks += chunks
                progress["processed"].append(src["name"])
            except: pass

    progress["total_processed"] = len(progress["processed"])
    save_progress(progress)

    print(f"\n{'='*50}")
    print(f"🎉 Batch complete! {len(batch)} sources → {total_chunks} chunks")
    print(f"   Total done: {progress['total_processed']}/{len(all_sources)}")
    if progress["total_processed"] < len(all_sources):
        print(f"   ⏳ আরও {len(all_sources) - progress['total_processed']} সোর্স বাকি — পরের রানে হবে")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
