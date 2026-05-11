#!/usr/bin/env python3
"""
Nobab_AI Universal Ingester v8.0 — Complete Raw Data Pipeline
Collection → Cleaning → Chunking → ChromaDB + JSONL Save
সব ডেটা datasets/raw_<domain>/ ফোল্ডারে JSONL হিসেবেও সেভ হবে।
"""

import os, json, requests, csv, io, time, re, chromadb
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from chromadb.utils import embedding_functions

# ══════════════ কনফিগ ══════════════
BATCH_SIZE = 200
PROGRESS_FILE = "source_progress.json"
CHROMA_PATH = "./chroma_db"
BATCH_ID = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
HDR = {"User-Agent": "Mozilla/5.0 (compatible; Nobab_AI/8.0)"}

# ══════════════ ChromaDB ══════════════
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
client = chromadb.PersistentClient(path=CHROMA_PATH)

# ══════════════ সোর্স লোডার ══════════════
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

# ══════════════ টেক্সট প্রসেসিং ══════════════
def safe_get(url, timeout=20):
    try:
        return requests.get(url, headers=HDR, timeout=timeout, allow_redirects=True)
    except:
        return None

def clean_text(raw):
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r'\s+', ' ', l).strip() for l in text.split("\n")]
    lines = [l for l in lines if len(l) > 40]
    seen = set()
    unique = [l for l in lines if not (l in seen or seen.add(l))]
    return "\n".join(unique)

def chunk_text(text, size=400):
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
    chunks = []
    for para in paragraphs:
        if len(para) <= size:
            chunks.append(para)
        else:
            sentences = [s.strip() + "." for s in para.replace("\n", " ").split(".") if s.strip()]
            cur = ""
            for s in sentences:
                if len(cur) + len(s) <= size:
                    cur += s + " "
                else:
                    if cur: chunks.append(cur.strip())
                    cur = s + " "
            if cur: chunks.append(cur.strip())
    return chunks

# ══════════════ সোর্স ইনজেস্ট ══════════════
def ingest_source(src):
    name = src.get("name", "unknown")
    url = src.get("url", "")
    domain = src.get("domain", "cyber")
    stype = src.get("type", "html")

    try:
        if stype in ["html", "xml", "github", "zenodo"]:
            r = safe_get(url)
            if not r or r.status_code != 200:
                print(f"  ⚠️ {name}: HTTP {r.status_code if r else 'timeout'}")
                return 0
            raw = clean_text(r.text[:80000])
        elif stype == "json":
            r = safe_get(url)
            if not r or r.status_code != 200:
                print(f"  ⚠️ {name}: HTTP {r.status_code if r else 'timeout'}")
                return 0
            raw = json.dumps(r.json(), indent=2)[:80000]
        elif stype == "csv":
            r = safe_get(url)
            if not r or r.status_code != 200:
                print(f"  ⚠️ {name}: HTTP {r.status_code if r else 'timeout'}")
                return 0
            rows = list(csv.DictReader(io.StringIO(r.text)))[:1000]
            raw = "\n".join([json.dumps(row, ensure_ascii=False) for row in rows])[:80000]
        else:
            return 0

        if not raw or len(raw) < 150:
            print(f"  ⚠️ {name}: content too short")
            return 0

        chunks = chunk_text(raw)
        if not chunks:
            print(f"  ⚠️ {name}: no valid chunks")
            return 0

        # ✅ ChromaDB save
        collection = get_collection(domain)
        ids = [f"{re.sub(r'[^a-zA-Z0-9]', '_', name)[:50]}_{i}_{BATCH_ID}" for i in range(len(chunks))]
        metas = [{"source": name, "domain": domain, "chunk": i} for i in range(len(chunks))]
        for i in range(0, len(chunks), 50):
            collection.add(documents=chunks[i:i+50], ids=ids[i:i+50], metadatas=metas[i:i+50])

        # ✅ JSONL save
        jsonl_dir = os.path.join("datasets", f"raw_{domain}")
        os.makedirs(jsonl_dir, exist_ok=True)
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)[:60]
        jsonl_path = os.path.join(jsonl_dir, f"{safe_name}_{BATCH_ID}.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps({"text": chunk, "source": name, "domain": domain}, ensure_ascii=False) + "\n")

        print(f"  ✅ {name}: {len(chunks)} chunks saved")
        return len(chunks)

    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:100]}")
        return 0

# ══════════════ মেইন ══════════════
def main():
    print(f"╔══════════════════════════════════════╗")
    print(f"║  Nobab_AI Universal Ingester v8.0  ║")
    print(f"║  Raw Text → ChromaDB + JSONL       ║")
    print(f"╚══════════════════════════════════════╝")
    print(f"📅 {datetime.utcnow()}\n")

    all_sources = load_all_sources()
    progress = load_progress()
    processed_names = set(progress["processed"])

    pending = [s for s in all_sources if s["name"] not in processed_names]
    batch = pending[:BATCH_SIZE]

    print(f"📋 Total: {len(all_sources)} | Already done: {len(processed_names)} | This batch: {len(batch)}\n")

    if not batch:
        print("✅ All sources already processed!")
        return

    total_chunks = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(ingest_source, s): s for s in batch}
        for f in as_completed(futures):
            src = futures[f]
            try:
                chunks = f.result()
                total_chunks += chunks
                progress["processed"].append(src["name"])
            except:
                pass

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
