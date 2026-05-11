#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║     Nobab_AI MASTER INGESTER — ALL-IN-ONE vFINAL              ║
║     Cyber + Medical + Physics + Dark Web — Raw Data            ║
║     ChromaDB + JSONL — Tor2Web Gateway (No Tor needed)         ║
║     একবার রান → সব ডেটা → RAG ব্যবহারের জন্য প্রস্তুত          ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, requests, time, re, csv, io, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ══════════════ CONFIG ══════════════
BASE_DIR = Path.home() / "Nobab_AI"
DATASET_DIRS = {
    "cyber_raw": BASE_DIR / "datasets" / "cyber_raw",
    "medical_raw": BASE_DIR / "datasets" / "medical_raw",
    "physics_raw": BASE_DIR / "datasets" / "physics_raw",
    "darkweb_raw": BASE_DIR / "datasets" / "darkweb_raw",
}
CHROMA_PATH = BASE_DIR / "chroma_db"
BATCH_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

for d in DATASET_DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

# Tor2Web গেটওয়ে (মে ২০২৬-এ UP)
GATEWAYS = ["onion.ly", "onion.pet"]
ONION_SOURCES = [
    "darkfailllnkf4vf.onion",
    "xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion",
    "tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion",
]

HDR = {"User-Agent": "Mozilla/5.0 (compatible; Nobab_AI/1.0)"}

# ══════════════ HELPERS ══════════════
def save_jsonl(data, directory, name):
    if not data: return 0
    path = directory / f"{name}_{BATCH_ID}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  ✅ {name}: {len(data)} records")
    return len(data)

def fetch_url(url, timeout=30):
    try:
        return requests.get(url, headers=HDR, timeout=timeout)
    except:
        return None

# ══════════════ 1. CYBER — CISA KEV + MITRE ATT&CK + NIST NVD ══════════════
def ingest_cyber():
    cyber_dir = DATASET_DIRS["cyber_raw"]
    total = 0

    # CISA KEV
    print("🔄 CISA KEV...")
    r = fetch_url("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    if r and r.status_code == 200:
        kev = r.json()
        qa = [{"question": f"What is {v.get('cveID','')}?", "answer": v.get("shortDescription",""), "source": "CISA KEV", "domain": "cyber"} for v in kev.get("vulnerabilities", []) if v.get("cveID")]
        total += save_jsonl(qa, cyber_dir, "cisa_kev")

    # MITRE ATT&CK
    print("🔄 MITRE ATT&CK...")
    r = fetch_url("https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json")
    if r and r.status_code == 200:
        attack = r.json()
        qa = []
        for obj in attack.get("objects", []):
            if obj.get("type") == "attack-pattern":
                tid = next((ref.get("external_id","") for ref in obj.get("external_references",[]) if ref.get("source_name")=="mitre-attack"), "")
                if obj.get("name") and obj.get("description"):
                    qa.append({"question": f"What is MITRE ATT&CK {tid}: {obj['name']}?", "answer": obj["description"][:1500], "source": "MITRE ATT&CK", "domain": "cyber"})
        total += save_jsonl(qa, cyber_dir, "mitre_attack")

    # NIST NVD
    print("🔄 NIST NVD...")
    r = fetch_url("https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=50")
    if r and r.status_code == 200:
        nvd = r.json()
        qa = []
        for vuln in nvd.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cid = cve.get("id", "")
            desc = next((d.get("value","") for d in cve.get("descriptions",[]) if d.get("lang")=="en"), "")
            if cid and desc:
                qa.append({"question": f"What is {cid}?", "answer": desc[:1500], "source": "NIST NVD", "domain": "cyber"})
        total += save_jsonl(qa, cyber_dir, "nist_nvd")

    print(f"🛡️ Cyber total: {total} records\n")
    return total

# ══════════════ 2. MEDICAL — ClinVar + BioASQ ══════════════
def ingest_medical():
    med_dir = DATASET_DIRS["medical_raw"]
    total = 0

    # ClinVar (NCBI E-utilities)
    print("🔄 ClinVar...")
    r = fetch_url("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&retmax=50&term=pathogenic[clinical_significance]&retmode=json")
    if r and r.status_code == 200:
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        qa = []
        for cid in ids[:20]:
            r2 = fetch_url(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id={cid}&retmode=json")
            if r2 and r2.status_code == 200:
                rec = r2.json().get("result", {}).get(cid, {})
                title = rec.get("title", "")
                gene = rec.get("gene_sort", "")
                if title and gene:
                    qa.append({"question": f"Clinical significance of {gene}: {title}?", "answer": f"Gene: {gene}. {title}. ClinVar ID: {cid}.", "source": "ClinVar (NCBI/NIH)", "domain": "medical"})
        total += save_jsonl(qa, med_dir, "clinvar")

    # BioASQ
    print("🔄 BioASQ...")
    r = fetch_url("https://zenodo.org/records/7655130/files/BioASQ-training12b.zip", timeout=120)
    if r and r.status_code == 200:
        try:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                qa = []
                for fname in zf.namelist():
                    if fname.endswith(".json"):
                        data = json.loads(zf.read(fname))
                        for item in data.get("questions", [])[:50]:
                            q, ideal = item.get("body",""), item.get("ideal_answer","")
                            if q and ideal:
                                qa.append({"question": q, "answer": ideal[:1500], "source": "BioASQ", "domain": "medical"})
                total += save_jsonl(qa, med_dir, "bioasq")
        except Exception as e:
            print(f"  ⚠️ BioASQ: {e}")

    print(f"🏥 Medical total: {total} records\n")
    return total

# ══════════════ 3. PHYSICS — arXiv ══════════════
def ingest_physics():
    phys_dir = DATASET_DIRS["physics_raw"]
    total = 0

    print("🔄 arXiv Physics...")
    url = "http://export.arxiv.org/api/query?search_query=cat:quant-ph+OR+cat:nucl-th+OR+cat:hep-th&start=0&max_results=30&sortBy=submittedDate&sortOrder=descending"
    r = fetch_url(url, timeout=30)
    if r and r.status_code == 200:
        root = ET.fromstring(r.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
        qa = []
        for entry in root.findall('atom:entry', ns):
            title_el = entry.find('atom:title', ns)
            summary_el = entry.find('atom:summary', ns)
            id_el = entry.find('atom:id', ns)
            if title_el is not None and summary_el is not None and id_el is not None:
                title = title_el.text.strip().replace('\n', ' ')
                summary = summary_el.text.strip().replace('\n', ' ')
                arxiv_id = id_el.text.strip().split('/abs/')[-1]
                if title and summary:
                    qa.append({"question": f"What does the paper '{title}' discuss?", "answer": f"arXiv ID: {arxiv_id}. Summary: {summary[:1500]}", "source": "arXiv Physics", "domain": "physics"})
        total += save_jsonl(qa, phys_dir, "arxiv_physics")

    print(f"⚛️ Physics total: {total} records\n")
    return total

# ══════════════ 4. DARK WEB — Tor2Web Gateway (No Tor!) ══════════════
def fetch_onion_via_gateway(onion, gw):
    url = f"https://{onion}.{gw}"
    try:
        r = requests.get(url, headers=HDR, timeout=45)
        if r.status_code == 200:
            return r.text[:15000]
    except:
        pass
    return None

def ingest_darkweb():
    dark_dir = DATASET_DIRS["darkweb_raw"]
    total = 0

    print("🕶️ Dark Web (Tor2Web Gateway)...")
    for onion in ONION_SOURCES:
        for gw in GATEWAYS:
            html = fetch_onion_via_gateway(onion, gw)
            if html:
                fname = re.sub(r"[^a-zA-Z0-9_\.]", "_", onion)[:50]
                qa = [{"text": html, "source": f"Dark Web ({onion})", "domain": "darkweb", "gateway": gw, "timestamp": datetime.now(timezone.utc).isoformat()}]
                total += save_jsonl(qa, dark_dir, fname)
                break  # একটা gateway কাজ করলেই পরের onion
            time.sleep(1)

    print(f"🕶️ Dark Web total: {total} sources\n")
    return total

# ══════════════ 5. ChromaDB INDEXING ══════════════
def index_to_chromadb():
    print("📚 ChromaDB indexing...")
    import chromadb
    from chromadb.utils import embedding_functions

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    DOMAIN_COLLECTIONS = {
        "cyber_raw": "cyber_defender",
        "medical_raw": "medical_knowledge",
        "physics_raw": "quantum_knowledge",
        "darkweb_raw": "darkweb_knowledge",
    }

    for dir_key, col_name in DOMAIN_COLLECTIONS.items():
        collection = client.get_or_create_collection(name=col_name, embedding_function=ef)
        data_dir = DATASET_DIRS[dir_key]
        if not data_dir.exists():
            continue
        docs, ids, metas = [], [], []
        for fpath in data_dir.glob("*.jsonl"):
            fname = fpath.name
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        text = d.get("text") or f"Q: {d.get('question','')}\nA: {d.get('answer','')}"
                        if text and len(text) > 30:
                            docs.append(text)
                            ids.append(f"{fname}_{len(ids)}_{int(time.time())}")
                            metas.append({"source": d.get("source",""), "file": fname})
                    except:
                        pass
        if docs:
            for i in range(0, len(docs), 100):
                collection.add(documents=docs[i:i+100], ids=ids[i:i+100], metadatas=metas[i:i+100])
            print(f"  ✅ {col_name}: {len(docs)} documents indexed")
    print("✅ ChromaDB indexing complete!\n")

# ══════════════ MAIN ══════════════
def main():
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║     Nobab_AI MASTER INGESTER — ALL-IN-ONE vFINAL              ║")
    print(f"║     Cyber + Medical + Physics + Dark Web — Raw Data            ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print(f"📅 {datetime.now(timezone.utc)}\n")

    grand_total = 0

    # Phase 1 — Cyber
    grand_total += ingest_cyber()

    # Phase 2 — Medical
    grand_total += ingest_medical()

    # Phase 3 — Physics
    grand_total += ingest_physics()

    # Phase 4 — Dark Web (Tor2Web Gateway)
    grand_total += ingest_darkweb()

    # Phase 5 — ChromaDB Indexing
    index_to_chromadb()

    print(f"{'='*60}")
    print(f"🎉 ALL DONE! Grand Total: {grand_total} records across all domains")
    print(f"📁 Data directories:")
    for key, d in DATASET_DIRS.items():
        file_count = len(list(d.glob("*.jsonl"))) if d.exists() else 0
        print(f"   {key}: {file_count} files → {d}")
    print(f"📚 ChromaDB: {CHROMA_PATH}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
