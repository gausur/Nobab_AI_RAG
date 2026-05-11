#!/usr/bin/env python3
"""
Nobab_AI Unified RAG Engine — Cyber + Medical + Bangla
Author: Nobab_AI Project
Version: 3.0.0 — Multilingual (EN + BN)
"""

import os, json, glob, time, chromadb, requests
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

# ======================== কনফিগারেশন ========================
class UnifiedConfig:
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"
    LLM_MODEL = "DeepSeek-R1"
    # ✅ মাল্টিলিঙ্গুয়াল এম্বেডিং (বাংলা সহ ৫০+ ভাষা)
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
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

# ======================== বাংলা ট্রান্সলেশন ইঞ্জিন ========================
class BengaliTranslator:
    """English ↔ Bangla ট্রান্সলেশন — OPUS-MT MarianMT দিয়ে"""
    def __init__(self):
        self.model_en2bn = None
        self.tokenizer_en2bn = None
        self.model_bn2en = None
        self.tokenizer_bn2en = None
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        try:
            from transformers import MarianMTModel, MarianTokenizer
            print("🔄 বাংলা ট্রান্সলেশন মডেল লোড হচ্ছে...")
            # English → Bangla
            self.tokenizer_en2bn = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-bn")
            self.model_en2bn = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-bn")
            # Bangla → English
            self.tokenizer_bn2en = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-bn-en")
            self.model_bn2en = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-bn-en")
            self._loaded = True
            print("✅ বাংলা ট্রান্সলেশন রেডি")
        except Exception as e:
            print(f"⚠️ ট্রান্সলেশন মডেল লোড ব্যর্থ: {e}")
            self._loaded = False

    def en2bn(self, text: str) -> str:
        """ইংরেজি → বাংলা"""
        if not self._loaded:
            self._load()
        if not self._loaded or not text:
            return text
        try:
            inputs = self.tokenizer_en2bn(text, return_tensors="pt", max_length=512, truncation=True)
            translated = self.model_en2bn.generate(**inputs, max_length=512)
            return self.tokenizer_en2bn.decode(translated[0], skip_special_tokens=True)
        except:
            return text

    def bn2en(self, text: str) -> str:
        """বাংলা → ইংরেজি"""
        if not self._loaded:
            self._load()
        if not self._loaded or not text:
            return text
        try:
            inputs = self.tokenizer_bn2en(text, return_tensors="pt", max_length=512, truncation=True)
            translated = self.model_bn2en.generate(**inputs, max_length=512)
            return self.tokenizer_bn2en.decode(translated[0], skip_special_tokens=True)
        except:
            return text

    def is_bangla(self, text: str) -> bool:
        """টেক্সট বাংলা কিনা চেক করে"""
        bangla_range = range(0x0980, 0x09FF)
        bangla_chars = sum(1 for c in text if ord(c) in bangla_range)
        return bangla_chars > len(text) * 0.15  # ১৫% অক্ষর বাংলা হলে


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
        self.translator = BengaliTranslator()

    def index_all(self):
        for domain, cfg in DOMAINS.items():
            collection = self.vs.get_collection(cfg["collection"])
            docs, ids, metas = load_jsonl_files(cfg["dataset_dir"])
            if docs:
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
        """প্রশ্ন করো — অটো বাংলা ডিটেক্ট + ট্রান্সলেশন"""
        original_q = question
        is_bn = self.translator.is_bangla(question)

        if is_bn:
            print(f"🇧🇩 বাংলা প্রশ্ন সনাক্ত হয়েছে")
            # বাংলা → ইংরেজি
            question_en = self.translator.bn2en(question)
            print(f"🔄 অনূদিত: {question_en[:100]}...")
        else:
            question_en = question

        # Search in ChromaDB
        results = self.search(question_en, domain)
        docs = results["documents"][0] if results["documents"] else []

        if not docs:
            print("❌ কোনো প্রাসঙ্গিক তথ্য পাওয়া যায়নি।")
            return

        print(f"📚 {len(docs)} প্রাসঙ্গিক ডকুমেন্ট পাওয়া গেছে")

        # Generate answer
        answer_en = self.generate(question_en, docs)

        # বাংলা প্রশ্ন → বাংলা উত্তর
        if is_bn:
            answer_bn = self.translator.en2bn(answer_en)
            print(f"\n📝 উত্তর (বাংলা):\n{answer_bn}")
        else:
            print(f"\n📝 উত্তর:\n{answer_en}")


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
            print("প্রশ্ন দাও: python unified_rag.py --ask 'তোমার প্রশ্ন'")
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
