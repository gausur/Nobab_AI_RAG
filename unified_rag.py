#!/usr/bin/env python3
"""
Nobab_AI Unified RAG Engine — Cyber + Medical
Author: Nobab_AI Project
Version: 2.0.0
"""

import os, json, glob, time, chromadb, requests
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

# ======================== কনফিগারেশন ========================
class UnifiedConfig:
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"
    LLM_MODEL = "DeepSeek-R1"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    CHROMA_PATH = "./chroma_db"
    N_RESULTS = 5

DOMAINS = {
    "cyber": {
        "collection": "cyber_defender",
        "dataset_dir": "datasets/cyber",
        "keywords": [
            "CVE", "exploit", "malware", "attack", "phishing", "ransomware",
            "firewall", "SQL injection", "Active Directory", "penetration",
            "Feodo", "QakBot", "MITRE", "Metasploit", "Burp Suite",
            "reverse shell", "privilege escalation", "XSS", "CSRF",
            "command and control", "botnet", "zero-day"
        ]
    },
    "medical": {
        "collection": "medical_knowledge",
        "dataset_dir": "datasets/medical",
        "keywords": [
            "gene", "protein", "disease", "treatment", "diagnosis", "clinical",
            "molecular", "pharmacology", "surgery", "cancer", "cardiology",
            "CRISPR", "mutation", "cell", "pathway", "receptor", "enzyme",
            "trial", "therapy", "radiology", "anatomy", "physiology"
        ]
    }
}

# ======================== ChromaDB সেটআপ ========================
class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=UnifiedConfig.CHROMA_PATH)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=UnifiedConfig.EMBEDDING_MODEL
        )

    def get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedding_fn
        )

# ======================== ডোমেইন ডিটেক্টর ========================
def detect_domain(question: str) -> str:
    scores = {}
    for domain, cfg in DOMAINS.items():
        scores[domain] = sum(1 for kw in cfg["keywords"] if kw.lower() in question.lower())
    return max(scores, key=scores.get, default="cyber")

# ======================== ডেটাসেট লোডার ========================
def load_jsonl_files(directory: str) -> tuple:
    docs, ids, metas = [], [], []
    pattern = os.path.join(directory, "*.jsonl")
    files = glob.glob(pattern)
    if not files:
        print(f"⚠️ {directory}-তে কোনো .jsonl ফাইল নেই")
        return docs, ids, metas

    for file_path in files:
        fname = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    q = data.get("question", "").strip()
                    a = data.get("answer", "").strip()
                    src = data.get("source", "unknown")
                    if q and a and len(a) > 50:
                        docs.append(f"Question: {q}\nAnswer: {a}")
                        ids.append(f"{fname}_{len(ids)}_{int(time.time())}")
                        metas.append({"source": src, "file": fname})
                except json.JSONDecodeError:
                    continue
    return docs, ids, metas

# ======================== RAG কোর ========================
class UnifiedRAG:
    def __init__(self):
        self.vs = VectorStore()

    def index_all(self):
        for domain, cfg in DOMAINS.items():
            collection = self.vs.get_collection(cfg["collection"])
            docs, ids, metas = load_jsonl_files(cfg["dataset_dir"])
            if docs:
                # ব্যাচে add
                for i in range(0, len(docs), 100):
                    collection.add(
                        documents=docs[i:i+100],
                        ids=ids[i:i+100],
                        metadatas=metas[i:i+100]
                    )
                print(f"✅ {domain}: {len(docs)} ডকুমেন্ট ইনডেক্স হয়েছে")
            else:
                print(f"ℹ️ {domain}: কোনো ডকুমেন্ট নেই, স্কিপ")

    def search(self, question: str, domain: str = None, top_k: int = 5):
        if domain is None:
            domain = detect_domain(question)
            print(f"🔍 অটো-ডোমেইন: {domain}")

        collection = self.vs.get_collection(DOMAINS[domain]["collection"])
        results = collection.query(query_texts=[question], n_results=top_k,
                                   include=["documents", "metadatas", "distances"])
        return results

    def generate(self, question: str, contexts: List[str]) -> str:
        if not UnifiedConfig.GITHUB_TOKEN:
            return "❌ GH_TOKEN সেট করা নেই।"

        ctx = "\n---\n".join(contexts)
        system_prompt = f"""You are an expert in {detect_domain(question)}. Answer using the provided context.
If the answer is not in the context, say: "I don't find enough information."

Context:
{ctx}"""

        headers = {
            "Authorization": f"Bearer {UnifiedConfig.GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": UnifiedConfig.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        try:
            resp = requests.post(
                f"{UnifiedConfig.GITHUB_MODELS_URL}/chat/completions",
                headers=headers, json=payload, timeout=120
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ LLM Error: HTTP {resp.status_code} - {resp.text[:200]}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def ask(self, question: str, domain: str = None):
        results = self.search(question, domain)
        docs = results["documents"][0] if results["documents"] else []
        if not docs:
            print("❌ কোনো প্রাসঙ্গিক তথ্য পাওয়া যায়নি।")
            return
        print(f"📚 {len(docs)} প্রাসঙ্গিক ডকুমেন্ট পাওয়া গেছে")
        answer = self.generate(question, docs)
        print(f"\n📝 উত্তর:\n{answer}")

# ======================== CLI ========================
def main():
    import sys
    rag = UnifiedRAG()
    if len(sys.argv) < 2:
        print("Usage: python unified_rag.py --index | --ask '<question>' [--domain cyber|medical]")
        return

    cmd = sys.argv[1]
    if cmd == "--index":
        rag.index_all()
    elif cmd == "--ask":
        if len(sys.argv) < 3:
            print("প্রশ্ন দাও: python unified_rag.py --ask 'What is Feodo C2?'")
            return
        question = sys.argv[2]
        domain = None
        if len(sys.argv) >= 5 and sys.argv[3] == "--domain":
            domain = sys.argv[4]
        rag.ask(question, domain)
    else:
        print(f"অজানা কমান্ড: {cmd}")

if __name__ == "__main__":
    main()
