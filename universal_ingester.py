#!/usr/bin/env python3
"""
Nobab_AI Universal Ingester v6.1 — Multiple Source Files Support
sources1.json, sources2.json, sources3.json থেকে সব সোর্স পড়ে নেয়
"""

import os, json, requests, csv, io, re, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

# ═══════════════════ CONFIG ═══════════════════
DOMAIN_DIRS = {
    "cyber": "datasets/cyber",
    "medical": "datasets/medical",
    "quantum": "datasets/quantum",
    "nuclear": "datasets/nuclear",
    "darkweb": "datasets/darkweb"
}
BATCH_ID = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
HDR = {"User-Agent": "Nobab_AI-Ingester/6.1"}
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

for d in DOMAIN_DIRS.values():
    os.makedirs(d, exist_ok=True)

# ═══════════════════ SOURCE LOADER ═══════════════════
def load_sources():
    """sources1.json, sources2.json, sources3.json থেকে সব সোর্স লোড"""
    all_sources = []
    for fname in ["sources1.json", "sources2.json", "sources3.json"]:
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_sources.extend(data)
                elif isinstance(data, dict) and "sources" in data:
                    all_sources.extend(data["sources"])
            print(f"📄 {fname}: {len(data) if isinstance(data, list) else len(data.get('sources', []))} sources loaded")
    return all_sources

# ═══════════════════ RAW TEXT PROCESSING ═══════════════════
def safe_get(url, timeout=30):
    try: return requests.get(url, headers=HDR, timeout=timeout)
    except: return None

def clean_text(raw):
    """HTML → clean text"""
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
    """Clean text → smaller chunks"""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
    chunks = []
    for para in paragraphs:
        if len(para) <= CHUNK_SIZE:
            chunks.append(para)
        else:
            sentences = [s.strip() + "." for s in para.replace("\n", " ").split(".") if s.strip()]
            current = ""
            for s in sentences:
                if len(current) + len(s) <= CHUNK_SIZE:
                    current += s + " "
                else:
                    if current: chunks.append(current.strip())
                    current = s + " "
            if current: chunks.append(current.strip())
    return chunks

# ═══════════════════ INGESTER ═══════════════════
def ingest_source(src, collection):
    """একটা সোর্স থেকে Raw Text → Clean → Chunk → ChromaDB"""
    name = src.get("name", "unknown")
    url = src.get("url", "")
    domain = src.get("domain", "cyber")
    stype = src.get("type", "html")

    try:
        if stype == "html":
            r = safe_get(url)
            if not r or r.status_code != 200:
                print(f"  ⚠️ {name}: HTTP {r.status_code if r else 'timeout'}")
                return 0
            raw = clean_text(r.text)
        elif stype == "json":
            r = safe_get(url)
            if not r or r.status_code != 200:
                print(f"  ⚠️ {name}: HTTP {r.status_code if r else 'timeout'}")
                return 0
            raw = json.dumps(r.json(), indent=2)[:50000]
        elif stype == "csv":
            r = safe_get(url)
            if not r or r.status_code != 200:
                print(f"  ⚠️ {name}: HTTP {r.status_code if r else 'timeout'}")
                return 0
            reader = csv.DictReader(io.StringIO(r.text))
            rows = list(reader)[:1000]
            raw = "\n".join([json.dumps(row, ensure_ascii=False) for row in rows])
        elif stype in ["xml", "github", "zenodo"]:
            r = safe_get(url)
            if not r or r.status_code != 200:
                print(f"  ⚠️ {name}: HTTP {r.status_code if r else 'timeout'}")
                return 0
            raw = r.text[:50000]
        else:
            return 0

        if not raw or len(raw) < 100:
            print(f"  ⚠️ {name}: Very little content ({len(raw)} chars)")
            return 0

        chunks = chunk_text(raw)
        if not chunks:
            return 0

        ids = [f"{name.replace(' ', '_')[:60]}_chunk_{i}_{BATCH_ID}" for i in range(len(chunks))]
        metadatas = [{"source": name, "url": url, "domain": domain, "chunk": i, "total": len(chunks)} for i in range(len(chunks))]

        for i in range(0, len(chunks), 100):
            collection.add(documents=chunks[i:i+100], ids=ids[i:i+100], metadatas=metadatas[i:i+100])

        print(f"  ✅ {name}: {len(chunks)} chunks indexed")
        return len(chunks)

    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:100]}")
        return 0

# ═══════════════════ MAIN ═══════════════════
def main():
    print(f"╔══════════════════════════════════════════╗")
    print(f"║  Nobab_AI Universal Ingester v6.1       ║")
    print(f"║  Multiple Source Files — Raw Text       ║")
    print(f"╚══════════════════════════════════════════╝")
    print(f"📅 {datetime.utcnow()}\n")

    # ChromaDB Setup
    import chromadb
    from chromadb.utils import embedding_functions
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    client = chromadb.PersistentClient(path="./chroma_db")

    sources = load_sources()
    print(f"📋 Total {len(sources)} sources loaded\n")

    total_chunks = 0
    for domain in ["cyber", "medical", "quantum", "nuclear", "darkweb"]:
        domain_sources = [s for s in sources if s.get("domain") == domain]
        if not domain_sources:
            continue
        collection = client.get_or_create_collection(name=f"raw_{domain}_knowledge", embedding_function=ef)
        print(f"🔄 Processing {domain} ({len(domain_sources)} sources)...")
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(ingest_source, s, collection): s for s in domain_sources}
            for f in as_completed(futures):
                try: total_chunks += f.result()
                except: pass

    print(f"\n{'='*50}")
    print(f"🎉 INGESTION COMPLETE! Total {total_chunks} chunks indexed")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
