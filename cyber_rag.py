#!/usr/bin/env python3
"""
Nobab_AI RAG Engine - Level 2
Cyber Defense Knowledge Retrieval System
Author: Nobab_AI Project
Version: 1.1.0 — Fixed ChromaDB persistence
"""

import os, json, glob, time, chromadb, requests
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Tuple, Optional

# ======================== কনফিগারেশন ========================

class RAGConfig:
    """RAG ইঞ্জিনের সেন্ট্রাল কনফিগারেশন"""
    DATASET_DIR: str = "."
    CHROMA_DB_PATH: str = "./chroma_db"
    COLLECTION_NAME: str = "cyber_defender_qa"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    GITHUB_MODELS_URL: str = "https://models.inference.ai.azure.com"
    LLM_MODEL: str = "DeepSeek-R1"
    DEFAULT_N_RESULTS: int = 5
    INDEX_BATCH_SIZE: int = 100


# ======================== ChromaDB সেটআপ ========================

class VectorStore:
    """ChromaDB ভেক্টর স্টোর ম্যানেজার — persistence ঠিক করা হয়েছে"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL
        )
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """
        ✅ ChromaDB best practice: get_or_create_collection ব্যবহার করো।
        এটি আগের ডেটা ডিলিট করবে না — শুধু না থাকলে নতুন বানাবে।
        """
        try:
            collection = self.client.get_or_create_collection(
                name=self.config.COLLECTION_NAME,
                embedding_function=self.embedding_fn,
                metadata={"description": "Nobab_AI Cyber Defense Knowledge Base"}
            )
            count = collection.count()
            if count > 0:
                print(f"📂 '{self.config.COLLECTION_NAME}' কালেকশন লোড ({count} ডকুমেন্ট)")
            else:
                print(f"✅ নতুন '{self.config.COLLECTION_NAME}' কালেকশন তৈরি")
            return collection
        except Exception as e:
            print(f"❌ কালেকশন তৈরি/লোড করতে সমস্যা: {e}")
            raise

    def reset_collection(self):
        """পুরো কালেকশন মুছে নতুন করে বানানো (শুধু --index এর সময়)"""
        try:
            self.client.delete_collection(self.config.COLLECTION_NAME)
            print(f"🗑️  পুরনো '{self.config.COLLECTION_NAME}' কালেকশন ডিলিট")
        except Exception:
            pass
        self.collection = self.client.create_collection(
            name=self.config.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"description": "Nobab_AI Cyber Defense Knowledge Base"}
        )
        print(f"✅ নতুন '{self.config.COLLECTION_NAME}' কালেকশন তৈরি (রিসেট)")

    def get_collection_stats(self) -> Dict[str, Any]:
        count = self.collection.count()
        return {
            "collection_name": self.config.COLLECTION_NAME,
            "total_documents": count,
            "embedding_model": self.config.EMBEDDING_MODEL,
            "storage_path": self.config.CHROMA_DB_PATH
        }


# ======================== ডেটাসেট ম্যানেজার ========================

class DatasetManager:
    """JSONL ডেটাসেট লোড ও ম্যানেজ"""

    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir

    def find_jsonl_files(self) -> List[str]:
        pattern = os.path.join(self.dataset_dir, "*.jsonl")
        files = glob.glob(pattern)
        return sorted(files)

    def load_qa_pairs(self, file_path: str) -> List[Dict[str, str]]:
        qa_pairs = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    question = data.get("question", "").strip()
                    answer = data.get("answer", "").strip()
                    source = data.get("source", "unknown")
                    if (question and answer
                            and question != f"Output from {source}"
                            and len(answer) > 50):
                        qa_pairs.append({
                            "question": question,
                            "answer": answer,
                            "source": source
                        })
                except json.JSONDecodeError:
                    continue
        return qa_pairs

    def load_all_datasets(self) -> Tuple[List[str], List[str], List[Dict]]:
        files = self.find_jsonl_files()
        print(f"📁 {len(files)} টি JSONL ফাইল পাওয়া গেছে")
        all_documents, all_ids, all_metadata = [], [], []
        total_qa = 0
        for file_path in files:
            file_name = os.path.basename(file_path)
            qa_pairs = self.load_qa_pairs(file_path)
            for i, qa in enumerate(qa_pairs):
                doc_text = f"Question: {qa['question']}\nAnswer: {qa['answer']}"
                doc_id = f"{file_name}_{i}_{int(time.time() * 1000)}"
                metadata = {
                    "source": qa["source"],
                    "file": file_name,
                    "question": qa["question"][:200],
                    "answer_length": len(qa["answer"]),
                    "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                all_documents.append(doc_text)
                all_ids.append(doc_id)
                all_metadata.append(metadata)
            total_qa += len(qa_pairs)
            print(f"  📄 {file_name}: {len(qa_pairs)} টি Q&A লোড হয়েছে")
        print(f"📊 মোট {total_qa} টি Q&A পেয়ার লোড হয়েছে")
        return all_documents, all_ids, all_metadata


# ======================== RAG ইঞ্জিন ========================

class RAGEngine:
    """মেইন RAG ইঞ্জিন: সার্চ + জেনারেট"""

    def __init__(self, config: RAGConfig, vector_store: VectorStore):
        self.config = config
        self.vector_store = vector_store

    def index_dataset(
        self,
        documents: List[str],
        ids: List[str],
        metadatas: List[Dict],
        reset_first: bool = False
    ) -> int:
        """
        ডেটাসেট ইনডেক্স করো।
        reset_first=True দিলে আগের ডেটা মুছে নতুন করে ইন্ডেক্স করবে।
        """
        if reset_first:
            self.vector_store.reset_collection()

        total = len(documents)
        batch_size = self.config.INDEX_BATCH_SIZE
        collection = self.vector_store.collection

        print(f"🔄 ইনডেক্সিং শুরু... (মোট {total} ডকুমেন্ট)")
        start_time = time.time()
        indexed_count = 0

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            try:
                collection.add(
                    documents=documents[start:end],
                    ids=ids[start:end],
                    metadatas=metadatas[start:end]
                )
                indexed_count += (end - start)
                elapsed = time.time() - start_time
                docs_per_sec = indexed_count / elapsed if elapsed > 0 else 0
                print(f"  ⏳ {indexed_count}/{total} ({indexed_count * 100 // total}%) "
                      f"- {docs_per_sec:.1f} docs/sec")
            except Exception as e:
                print(f"  ❌ ব্যাচ {start}-{end} ইন্ডেক্স করতে সমস্যা: {e}")
                continue

        elapsed = time.time() - start_time
        print(f"✅ ইনডেক্সিং সম্পন্ন! {indexed_count} ডকুমেন্ট, সময়: {elapsed:.1f}s")
        return indexed_count

    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        ✅ ChromaDB query_texts ব্যবহার — collection-এই embedding_function
        সেট করা থাকায় ChromaDB নিজেই একই মডেল দিয়ে embed করবে।
        """
        collection = self.vector_store.collection
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        return {
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0]
        }

    def generate_answer(self, query: str, context_docs: List[str]) -> str:
        """GitHub Models (DeepSeek-R1) দিয়ে উত্তর জেনারেট"""
        token = os.getenv("GH_TOKEN")
        if not token:
            return "❌ GH_TOKEN সেট করা নেই। GitHub Secrets-এ GH_TOKEN যোগ করো।"

        context = "\n---\n".join(context_docs)

        system_prompt = f"""You are a Red Team cybersecurity expert and PhD-level researcher.
Answer the user's question using ONLY the provided context.
If the answer is not in the context, say: "I don't find enough information in the knowledge base."

Your answer MUST include:
1. Technical mechanisms or attack vectors
2. Specific CVEs, tools, or commands
3. Mitigation strategies
4. Real-world examples (if available)

Context:
{context}"""

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.config.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }

        try:
            resp = requests.post(
                f"{self.config.GITHUB_MODELS_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ LLM Error: HTTP {resp.status_code} - {resp.text[:200]}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def ask(self, query: str) -> str:
        """পূর্ণ RAG প্রশ্নোত্তর: সার্চ → জেনারেট"""
        print(f"\n🔍 প্রশ্ন: {query}")

        # Step 1: Retrieve
        search_results = self.search(query)
        documents = search_results["documents"]
        distances = search_results["distances"]

        if not documents:
            return "❌ কোনো প্রাসঙ্গিক তথ্য পাওয়া যায়নি।"

        print(f"📚 {len(documents)} টি প্রাসঙ্গিক ডকুমেন্ট পাওয়া গেছে")
        for i, (doc, dist) in enumerate(zip(documents[:3], distances[:3])):
            print(f"  {i + 1}. Distance: {dist:.4f} | Preview: {doc[:80]}...")

        # Step 2: Generate
        print("🤖 উত্তর জেনারেট করা হচ্ছে...")
        answer = self.generate_answer(query, documents)
        return answer


# ======================== CLI ইন্টারফেস ========================

def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║           🛡️  Nobab_AI RAG Engine  🛡️       ║
║        Cyber Defense Knowledge Base         ║
║              Version 1.1.0                  ║
╚══════════════════════════════════════════════╝
    """)

def print_help():
    print("""
📋 উপলভ্য কমান্ড:

  python cyber_rag.py --index              সব JSONL ফাইল ইন্ডেক্স করবে (reset)
  python cyber_rag.py --index file.jsonl   নির্দিষ্ট ফাইল ইন্ডেক্স করবে
  python cyber_rag.py --ask "প্রশ্ন"       প্রশ্নের উত্তর দেবে
  python cyber_rag.py --stats              কালেকশন স্ট্যাটাস দেখাবে
  python cyber_rag.py --help               এই মেনু দেখাবে
    """)


def main():
    print_banner()

    config = RAGConfig()
    vector_store = VectorStore(config)
    dataset_manager = DatasetManager(config.DATASET_DIR)
    engine = RAGEngine(config, vector_store)

    import sys

    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        print_help()
        return

    command = sys.argv[1]

    if command == "--index":
        if len(sys.argv) > 2:
            # নির্দিষ্ট ফাইল (reset ছাড়া — ম্যানুয়ালি চাইলে reset_first=True দিও)
            file_path = sys.argv[2]
            print(f"📄 {file_path} ইনডেক্স করা হচ্ছে...")
            qa_pairs = dataset_manager.load_qa_pairs(file_path)
            docs, ids, metas = [], [], []
            for i, qa in enumerate(qa_pairs):
                doc_text = f"Question: {qa['question']}\nAnswer: {qa['answer']}"
                docs.append(doc_text)
                ids.append(f"{os.path.basename(file_path)}_{i}")
                metas.append({"source": qa["source"]})
            count = engine.index_dataset(docs, ids, metas, reset_first=False)
            print(f"✅ {count} ডকুমেন্ট ইনডেক্স হয়েছে")
        else:
            # সব ফাইল — reset করে fresh index
            docs, ids, metas = dataset_manager.load_all_datasets()
            if docs:
                count = engine.index_dataset(docs, ids, metas, reset_first=True)
                print(f"✅ মোট {count} ডকুমেন্ট ইনডেক্স হয়েছে")
            else:
                print("⚠️ কোনো JSONL ফাইল পাওয়া যায়নি।")

    elif command == "--ask":
        if len(sys.argv) < 3:
            print("⚠️ প্রশ্ন দাও: python cyber_rag.py --ask \"তোমার প্রশ্ন\"")
            return
        query = " ".join(sys.argv[2:])
        answer = engine.ask(query)
        print(f"\n📝 উত্তর:\n{answer}")

    elif command == "--stats":
        stats = vector_store.get_collection_stats()
        print("\n📊 কালেকশন স্ট্যাটাস:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    else:
        print(f"❌ অজানা কমান্ড: {command}")
        print_help()


if __name__ == "__main__":
    main()
