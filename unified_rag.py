#!/usr/bin/env python3
"""
Nobab_AI Unified RAG Engine v5.0 — Multilingual (EN + BN)
Bengali Translator already integrated.
"""

import os, json, glob, time, chromadb, requests
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

class UnifiedConfig:
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"
    LLM_MODEL = "DeepSeek-R1"
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    CHROMA_PATH = "./chroma_db"
    N_RESULTS = 5

DOMAINS = {
    "cyber": {"collection": "cyber_defender", "dataset_dir": "datasets/cyber",
        "keywords": ["CVE", "exploit", "malware", "attack", "phishing", "ransomware", "firewall", "SQL injection", "pentest", "Feodo", "QakBot", "MITRE"]},
    "medical": {"collection": "medical_knowledge", "dataset_dir": "datasets/medical",
        "keywords": ["gene", "protein", "disease", "treatment", "diagnosis", "clinical", "molecular", "pharmacology", "surgery", "cancer", "cardiology", "CRISPR"]},
    "quantum": {"collection": "quantum_knowledge", "dataset_dir": "datasets/quantum",
        "keywords": ["quantum", "qubit", "entanglement", "superposition", "QKD", "cryptography", "photon", "ion trap", "annealing", "circuit", "algorithm"]},
    "nuclear": {"collection": "nuclear_knowledge", "dataset_dir": "datasets/nuclear",
        "keywords": ["nuclear", "proton", "neutron", "collision", "reactor", "decay", "fission", "fusion", "isotope", "radiation", "dosimetry"]},
    "darkweb": {"collection": "darkweb_knowledge", "dataset_dir": "datasets/darkweb",
        "keywords": ["dark web", "Tor", "onion", "I2P", "Freenet", "cryptocurrency", "ransomware leak", "hacker forum", "marketplace", "anonymity"]},
    # raw collections for universal ingester
    "raw_cyber": {"collection": "raw_cyber_knowledge", "dataset_dir": "datasets/raw_cyber", "keywords": ["CVE", "exploit", "malware", "attack", "phishing", "ransomware", "firewall", "pentest", "Feodo", "QakBot", "MITRE"]},
    "raw_medical": {"collection": "raw_medical_knowledge", "dataset_dir": "datasets/raw_medical", "keywords": ["gene", "protein", "disease", "treatment", "diagnosis", "clinical", "molecular", "pharmacology", "surgery", "cancer", "cardiology", "CRISPR"]},
    "raw_quantum": {"collection": "raw_quantum_knowledge", "dataset_dir": "datasets/raw_quantum", "keywords": ["quantum", "qubit", "entanglement", "superposition", "QKD", "cryptography", "photon", "ion trap", "annealing", "circuit", "algorithm"]},
    "raw_nuclear": {"collection": "raw_nuclear_knowledge", "dataset_dir": "datasets/raw_nuclear", "keywords": ["nuclear", "proton", "neutron", "collision", "reactor", "decay", "fission", "fusion", "isotope", "radiation", "dosimetry"]},
    "raw_darkweb": {"collection": "raw_darkweb_knowledge", "dataset_dir": "datasets/raw_darkweb", "keywords": ["dark web", "Tor", "onion", "I2P", "Freenet", "cryptocurrency", "ransomware leak", "hacker forum", "marketplace", "anonymity"]},
}

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
    def en2bn(self, t):
        if not self.ready: return t
        inp = self.tok_en2bn(t, return_tensors="pt", max_length=512, truncation=True)
        return self.tok_en2bn.decode(self.mod_en2bn.generate(**inp, max_length=512)[0], skip_special_tokens=True)
    def bn2en(self, t):
        if not self.ready: return t
        inp = self.tok_bn2en(t, return_tensors="pt", max_length=512, truncation=True)
        return self.tok_bn2en.decode(self.mod_bn2en.generate(**inp, max_length=512)[0], skip_special_tokens=True)
    def is_bangla(self, t):
        bn = range(0x0980, 0x09FF)
        total = len([c for c in t if c.strip()])
        if total == 0: return False
        bangla = sum(1 for c in t if ord(c) in bn)
        return bangla > total * 0.15

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=UnifiedConfig.CHROMA_PATH)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=UnifiedConfig.EMBEDDING_MODEL)
    def get_collection(self, name):
        return self.client.get_or_create_collection(name=name, embedding_function=self.ef)

def detect_domain(question):
    scores = {d: sum(1 for kw in cfg["keywords"] if kw.lower() in question.lower()) for d, cfg in DOMAINS.items()}
    return max(scores, key=scores.get, default="cyber")

class UnifiedRAG:
    def __init__(self):
        self.vs = VectorStore()
        self.trans = BengaliTranslator()
    def index_all(self):
        for d, c in DOMAINS.items():
            col = self.vs.get_collection(c["collection"])
            docs, ids, metas = [], [], []
            for fpath in glob.glob(os.path.join(c["dataset_dir"], "*.jsonl")):
                fname = os.path.basename(fpath)
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            text = data.get("text") or f"Q: {data.get('question','')}\nA: {data.get('answer','')}"
                            if text and len(text) > 30:
                                docs.append(text)
                                ids.append(f"{fname}_{len(ids)}_{int(time.time())}")
                                metas.append({"source": data.get("source", ""), "file": fname})
                        except: pass
            if docs:
                for i in range(0, len(docs), 100):
                    col.add(documents=docs[i:i+100], ids=ids[i:i+100], metadatas=metas[i:i+100])
                print(f"✅ {d}: {len(docs)} documents indexed")
    def search(self, question, domain=None, top_k=5):
        if domain is None: domain = detect_domain(question)
        col = self.vs.get_collection(DOMAINS[domain]["collection"])
        return col.query(query_texts=[question], n_results=top_k, include=["documents", "metadatas", "distances"])
    def generate(self, question, contexts):
        if not UnifiedConfig.GITHUB_TOKEN: return "GH_TOKEN missing"
        ctx = "\n---\n".join(contexts)
        sys = f"""You are a world-class expert in {detect_domain(question)}. Answer using ONLY the provided context. Be detailed and technical.

Context:
{ctx}"""
        headers = {"Authorization": f"Bearer {UnifiedConfig.GITHUB_TOKEN}", "Content-Type": "application/json"}
        payload = {"model": UnifiedConfig.LLM_MODEL, "messages": [{"role": "system", "content": sys}, {"role": "user", "content": question}], "temperature": 0.7, "max_tokens": 2048}
        try:
            r = requests.post(f"{UnifiedConfig.GITHUB_MODELS_URL}/chat/completions", headers=headers, json=payload, timeout=120)
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
        if is_bn: ans = self.trans.en2bn(ans)
        print(f"\n📝 উত্তর:\n{ans}")

def main():
    import sys
    rag = UnifiedRAG()
    if len(sys.argv) < 2:
        print("Usage: python unified_rag.py --index | --ask '<question>' | --stats")
        return
    cmd = sys.argv[1]
    if cmd == "--index": rag.index_all()
    elif cmd == "--ask" and len(sys.argv) > 2: rag.ask(" ".join(sys.argv[2:]))
    elif cmd == "--stats":
        import chromadb as cdb
        client = cdb.PersistentClient(path="./chroma_db")
        for col in client.list_collections(): print(f"📁 {col.name}: {col.count()} documents")

if __name__ == "__main__":
    main()
