#!/usr/bin/env python3
"""
Nobab_AI Unified RAG Engine v5.0 — Multilingual (EN + BN)
Bengali Translator already integrated — no separate step needed
"""

import os, json, glob, time, chromadb, requests
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

# ═══════════════════ CONFIG ═══════════════════
class UnifiedConfig:
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"
    LLM_MODEL = "DeepSeek-R1"
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    CHROMA_PATH = "./chroma_db"
    N_RESULTS = 5

DOMAINS = {
    "cyber": {
        "collection": "cyber_defender",
        "dataset_dir": "datasets/cyber",
        "keywords": ["CVE", "exploit", "malware", "attack", "phishing", "ransomware",
                     "firewall", "SQL injection", "pentest", "Feodo", "QakBot", "MITRE"]
    },
    "medical": {
        "collection": "medical_knowledge",
        "dataset_dir": "datasets/medical",
        "keywords": ["gene", "protein", "disease", "treatment", "diagnosis", "clinical",
                     "molecular", "pharmacology", "surgery", "cancer", "cardiology", "CRISPR"]
    },
    "quantum": {
        "collection": "quantum_knowledge",
        "dataset_dir": "datasets/quantum",
        "keywords": ["quantum", "qubit", "entanglement", "superposition", "QKD", "cryptography",
                     "photon", "ion trap", "annealing", "circuit", "algorithm"]
    },
    "nuclear": {
        "collection": "nuclear_knowledge",
        "dataset_dir": "datasets/nuclear",
        "keywords": ["nuclear", "proton", "neutron", "collision", "reactor", "decay",
                     "fission", "fusion", "isotope", "radiation", "dosimetry"]
    },
    "darkweb": {
        "collection": "darkweb_knowledge",
        "dataset_dir": "datasets/darkweb",
        "keywords": ["dark web", "Tor", "onion", "I2P", "Freenet", "cryptocurrency",
                     "ransomware leak", "hacker forum", "marketplace", "anonymity"]
    }
}

# ═══════════════════ BENGALI TRANSLATOR ═══════════════════
class BengaliTranslator:
    def __init__(self):
        try:
            from transformers import MarianMTModel, MarianTokenizer
            self.tok_en2bn = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-bn")
            self.mod_en2bn = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-bn")
            self.tok_bn2en = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-bn-en")
            self.mod_bn2en = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-bn-en")
            self.ready = True
        except:
            self.ready = False

    def en2bn(self, text):
        if not self.ready: return text
        inp = self.tok_en2bn(text, return_tensors="pt", max_length=512, truncation=True)
        return self.tok_en2bn.decode(self.mod_en2bn.generate(**inp, max_length=512)[0], skip_special_tokens=True)

    def bn2en(self, text):
        if not self.ready: return text
        inp = self.tok_bn2en(text, return_tensors="pt", max_length=512, truncation=True)
        return self.tok_bn2en.decode(self.mod_bn2en.generate(**inp, max_length=512)[0], skip_special_tokens=True)

    def is_bangla(self, text):
        bn_range = range(0x0980, 0x09FF)
        total = len([c for c in text if c.strip()])
        if total == 0: return False
        bangla = sum(1 for c in text if ord(c) in bn_range)
        return bangla > total * 0.15


# ═══════════════════ CHROMADB ═══════════════════
class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=UnifiedConfig.CHROMA_PATH)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=UnifiedConfig.EMBEDDING_MODEL)

    def get_collection(self, name):
        return self.client.get_or_create_collection(name=name, embedding_function=self.ef)


def detect_domain(question):
    scores = {}
    for domain, cfg in DOMAINS.items():
        scores[domain] = sum(1 for kw in cfg["keywords"] if kw.lower() in question.lower())
    return max(scores, key=scores.get, default="cyber")


# ═══════════════════ RAG ENGINE ═══════════════════
class UnifiedRAG:
    def __init__(self):
        self.vs = VectorStore()
        self.trans = BengaliTranslator()

    def index_all(self):
        for domain, cfg in DOMAINS.items():
            col = self.vs.get_collection(cfg["collection"])
            docs, ids, metas = [], [], []
            for fpath in glob.glob(os.path.join(cfg["dataset_dir"], "*.jsonl")):
                fname = os.path.basename(fpath)
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            d = json.loads(line)
                            q, a = d.get("question", "").strip(), d.get("answer", "").strip()
                            if q and a and len(a) > 30:
                                docs.append(f"Q: {q}\nA: {a}")
                                ids.append(f"{fname}_{len(ids)}_{int(time.time())}")
                                metas.append({"source": d.get("source", ""), "file": fname})
                        except: pass
            if docs:
                for i in range(0, len(docs), 100):
                    col.add(documents=docs[i:i+100], ids=ids[i:i+100], metadatas=metas[i:i+100])
                print(f"✅ {domain}: {len(docs)} ডকুমেন্ট ইনডেক্স")

    def search(self, question, domain=None, top_k=5):
        if domain is None:
            domain = detect_domain(question)
        col = self.vs.get_collection(DOMAINS[domain]["collection"])
        return col.query(query_texts=[question], n_results=top_k,
                        include=["documents", "metadatas", "distances"])

    def generate(self, question, contexts):
        if not UnifiedConfig.GITHUB_TOKEN:
            return "GH_TOKEN missing"
        ctx = "\n---\n".join(contexts)
        sys_prompt = f"""You are a world-class expert in {detect_domain(question)}. Answer using ONLY the provided context. Be detailed and technical.

Context:
{ctx}"""
        headers = {"Authorization": f"Bearer {UnifiedConfig.GITHUB_TOKEN}", "Content-Type": "application/json"}
        payload = {"model": UnifiedConfig.LLM_MODEL, "messages": [
            {"role": "system", "content": sys_prompt}, {"role": "user", "content": question}],
            "temperature": 0.7, "max_tokens": 2048}
        try:
            r = requests.post(f"{UnifiedConfig.GITHUB_MODELS_URL}/chat/completions",
                            headers=headers, json=payload, timeout=120)
            return r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else f"LLM Error: {r.status_code}"
        except Exception as e:
            return f"Error: {e}"

    def ask(self, question, domain=None):
        is_bn = self.trans.is_bangla(question)
        if is_bn:
            print("🇧🇩 বাংলা সনাক্ত")
            question = self.trans.bn2en(question)

        results = self.search(question, domain)
        docs = results["documents"][0] if results["documents"] else []
        if not docs:
            print("❌ কোনো তথ্য পাওয়া যায়নি")
            return

        print(f"📚 {len(docs)} ডকুমেন্ট পাওয়া গেছে")
        ans = self.generate(question, docs)

        if is_bn:
            ans = self.trans.en2bn(ans)

        print(f"\n📝 উত্তর:\n{ans}")


# ═══════════════════ CLI ═══════════════════
def main():
    import sys
    rag = UnifiedRAG()
    if len(sys.argv) < 2:
        print("Usage: python unified_rag.py --index | --ask '<question>'")
        return
    cmd = sys.argv[1]
    if cmd == "--index": rag.index_all()
    elif cmd == "--ask" and len(sys.argv) > 2: rag.ask(" ".join(sys.argv[2:]))

if __name__ == "__main__":
    main()
