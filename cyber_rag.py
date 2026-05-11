#!/usr/bin/env python3
"""
Nobab_AI RAG Engine - Level 2
Cyber Defense Knowledge Retrieval System
Author: Nobab_AI Project
Version: 1.0.0
"""

import os
import json
import glob
import time
import chromadb
from chromadb.utils import embedding_functions
import requests
from typing import List, Tuple, Optional, Dict, Any

# ======================== কনফিগারেশন ========================

class RAGConfig:
    """RAG ইঞ্জিনের সেন্ট্রাল কনফিগারেশন"""
    
    # ডিরেক্টরি ও ফাইল পাথ
    DATASET_DIR: str = "."                    # JSONL ফাইলগুলো যেখানে আছে
    CHROMA_DB_PATH: str = "./chroma_db"       # ChromaDB ডেটা স্টোর
    COLLECTION_NAME: str = "cyber_defender_qa" # কালেকশনের নাম
    
    # এম্বেডিং কনফিগ
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # লোকাল এম্বেডিং (ফ্রি)
    
    # GitHub Models কনফিগ (ফ্রি LLM)
    GITHUB_MODELS_URL: str = "https://models.inference.ai.azure.com"
    LLM_MODEL: str = "DeepSeek-R1"            # ফ্রি LLM মডেল
    
    # সার্চ কনফিগ
    DEFAULT_N_RESULTS: int = 5                # কতগুলো রেজাল্ট আনবে
    SIMILARITY_THRESHOLD: float = 0.3         # ন্যূনতম সাদৃশ্য স্কোর
    
    # ব্যাচ প্রসেসিং
    INDEX_BATCH_SIZE: int = 100


# ======================== ChromaDB সেটআপ ========================

class VectorStore:
    """ChromaDB ভেক্টর স্টোর ম্যানেজার"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        
        # ChromaDB ক্লায়েন্ট (Persistent)
        self.client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        
        # এম্বেডিং ফাংশন (Sentence Transformers - সম্পূর্ণ ফ্রি)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL
        )
        
        # কালেকশন তৈরি বা লোড
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """কালেকশন তৈরি বা লোড করা"""
        try:
            # আগের কালেকশন ডিলিট করে নতুন করে তৈরি (ফ্রেশ স্টার্ট)
            try:
                self.client.delete_collection(self.config.COLLECTION_NAME)
                print(f"🗑️  পুরনো '{self.config.COLLECTION_NAME}' কালেকশন ডিলিট করা হলো")
            except:
                pass  # না থাকলে কিছু করার দরকার নেই
            
            collection = self.client.create_collection(
                name=self.config.COLLECTION_NAME,
                embedding_function=self.embedding_fn,
                metadata={"description": "Nobab_AI Cyber Defense Knowledge Base"}
            )
            print(f"✅ নতুন '{self.config.COLLECTION_NAME}' কালেকশন তৈরি হয়েছে")
            return collection
        except Exception as e:
            print(f"❌ কালেকশন তৈরি করতে সমস্যা: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """কালেকশনের পরিসংখ্যান"""
        count = self.collection.count()
        return {
            "collection_name": self.config.COLLECTION_NAME,
            "total_documents": count,
            "embedding_model": self.config.EMBEDDING_MODEL,
            "storage_path": self.config.CHROMA_DB_PATH
        }


# ======================== ডেটাসেট ম্যানেজার ========================

class DatasetManager:
    """JSONL ডেটাসেট লোড ও ম্যানেজ করার ক্লাস"""
    
    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir
    
    def find_jsonl_files(self) -> List[str]:
        """সব JSONL ফাইল খুঁজে বের করা"""
        pattern = os.path.join(self.dataset_dir, "*.jsonl")
        files = glob.glob(pattern)
        return sorted(files)
    
    def load_qa_pairs(self, file_path: str) -> List[Dict[str, str]]:
        """একটি JSONL ফাইল থেকে Q&A লোড করা"""
        qa_pairs = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    question = data.get("question", "").strip()
                    answer = data.get("answer", "").strip()
                    source = data.get("source", "unknown")
                    
                    # বৈধ Q&A চেক
                    if (question and answer and
                        question != f"Output from {source}" and
                        len(answer) > 50):
                        qa_pairs.append({
                            "question": question,
                            "answer": answer,
                            "source": source
                        })
                except json.JSONDecodeError:
                    continue
        
        return qa_pairs
    
    def load_all_datasets(self) -> Tuple[List[str], List[str], List[Dict]]:
        """সব JSONL ফাইল থেকে সব Q&A লোড করো"""
        files = self.find_jsonl_files()
        print(f"📁 {len(files)} টি JSONL ফাইল পাওয়া গেছে")
        
        all_documents = []
        all_ids = []
        all_metadata = []
        
        total_qa = 0
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            qa_pairs = self.load_qa_pairs(file_path)
            
            for i, qa in enumerate(qa_pairs):
                # ডকুমেন্ট তৈরি: প্রশ্ন+উত্তর একসাথে
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
        metadatas: List[Dict]
    ) -> int:
        """ডেটাসেট ইনডেক্স করা (ChromaDB-তে ভেক্টর হিসেবে জমা)"""
        total = len(documents)
        batch_size = self.config.INDEX_BATCH_SIZE
        collection = self.vector_store.collection
        
        print(f"🔄 ইনডেক্সিং শুরু হচ্ছে... (মোট {total} ডকুমেন্ট)")
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
                
                print(f"  ⏳ {indexed_count}/{total} ({indexed_count*100//total}%) "
                      f"- {docs_per_sec:.1f} docs/sec")
                
            except Exception as e:
                print(f"  ❌ ব্যাচ {start}-{end} ইন্ডেক্স করতে সমস্যা: {e}")
                continue
        
        elapsed = time.time() - start_time
        print(f"✅ ইনডেক্সিং সম্পন্ন! {indexed_count} ডকুমেন্ট, সময়: {elapsed:.1f}s")
        return indexed_count
    
    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """প্রশ্নের জন্য সবচেয়ে প্রাসঙ্গিক ডকুমেন্ট খোঁজা"""
        
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
        """GitHub Models (DeepSeek-R1) দিয়ে উত্তর জেনারেট করা"""
        
        token = os.getenv("GH_TOKEN")
        if not token:
            return "❌ GH_TOKEN এনভায়রনমেন্ট ভেরিয়েবল সেট করা নেই।"
        
        # কনটেক্সট তৈরি
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
            print(f"  {i+1}. Distance: {dist:.4f} | Preview: {doc[:80]}...")
        
        # Step 2: Generate
        print("🤖 উত্তর জেনারেট করা হচ্ছে...")
        answer = self.generate_answer(query, documents)
        
        return answer


# ======================== CLI ইন্টারফেস ========================

def print_banner():
    """Nobab_AI ব্যানার"""
    print("""
╔══════════════════════════════════════════════╗
║           🛡️  Nobab_AI RAG Engine  🛡️       ║
║        Cyber Defense Knowledge Base         ║
║              Version 1.0.0                  ║
╚══════════════════════════════════════════════╝
    """)

def print_help():
    """হেল্প মেনু"""
    print("""
📋 উপলভ্য কমান্ড:

  python cyber_rag.py --index          সব JSONL ফাইল ইন্ডেক্স করবে
  python cyber_rag.py --index file.jsonl   নির্দিষ্ট ফাইল ইন্ডেক্স করবে
  python cyber_rag.py --ask "প্রশ্ন"     প্রশ্নের উত্তর দেবে
  python cyber_rag.py --interactive     ইন্টারঅ্যাক্টিভ মোড (একের পর এক প্রশ্ন)
  python cyber_rag.py --stats           কালেকশন স্ট্যাটাস দেখাবে
  python cyber_rag.py --help            এই মেনু দেখাবে
  
উদাহরণ:
  python cyber_rag.py --index
  python cyber_rag.py --ask "How to defend against Feodo C2?"
    """)

def interactive_mode(engine: RAGEngine):
    """ইন্টারঅ্যাক্টিভ প্রশ্নোত্তর মোড"""
    print("\n🔄 ইন্টারঅ্যাক্টিভ মোড (বের হতে 'exit' বা 'quit' টাইপ করো)\n")
    
    while True:
        try:
            query = input("❓ প্রশ্ন: ").strip()
            
            if query.lower() in ["exit", "quit", "q"]:
                print("👋 শেষ হচ্ছে...")
                break
            
            if not query:
                continue
            
            answer = engine.ask(query)
            print(f"\n📝 উত্তর:\n{answer}\n")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n👋 শেষ হচ্ছে...")
            break

# ======================== মেইন ========================

def main():
    print_banner()
    
    # কনফিগ ও ভেক্টর স্টোর সেটআপ
    config = RAGConfig()
    vector_store = VectorStore(config)
    
    # ডেটাসেট ম্যানেজার
    dataset_manager = DatasetManager(config.DATASET_DIR)
    
    # RAG ইঞ্জিন
    engine = RAGEngine(config, vector_store)
    
    # CLI আর্গুমেন্ট
    import sys
    
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        print_help()
        return
    
    command = sys.argv[1]
    
    # --index: ডেটাসেট ইনডেক্সিং
    if command == "--index":
        if len(sys.argv) > 2:
            # নির্দিষ্ট ফাইল
            file_path = sys.argv[2]
            print(f"📄 {file_path} ইনডেক্স করা হচ্ছে...")
            qa_pairs = dataset_manager.load_qa_pairs(file_path)
            docs, ids, metas = [], [], []
            for i, qa in enumerate(qa_pairs):
                doc_text = f"Question: {qa['question']}\nAnswer: {qa['answer']}"
                docs.append(doc_text)
                ids.append(f"{os.path.basename(file_path)}_{i}")
                metas.append({"source": qa["source"]})
            
            count = engine.index_dataset(docs, ids, metas)
            print(f"✅ {count} ডকুমেন্ট ইনডেক্স হয়েছে")
        else:
            # সব ফাইল
            docs, ids, metas = dataset_manager.load_all_datasets()
            if docs:
                count = engine.index_dataset(docs, ids, metas)
                print(f"✅ মোট {count} ডকুমেন্ট ইনডেক্স হয়েছে")
            else:
                print("⚠️ কোনো JSONL ফাইল পাওয়া যায়নি।")
    
    # --stats: পরিসংখ্যান
    elif command == "--stats":
        stats = vector_store.get_collection_stats()
        print("\n📊 কালেকশন স্ট্যাটাস:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    # --ask: প্রশ্নোত্তর
    elif command == "--ask":
        if len(sys.argv) < 3:
            print("⚠️ প্রশ্ন দাও: python cyber_rag.py --ask \"তোমার প্রশ্ন\"")
            return
        
        query = " ".join(sys.argv[2:])
        answer = engine.ask(query)
        print(f"\n📝 উত্তর:\n{answer}")
    
    # --interactive: ইন্টারঅ্যাক্টিভ মোড
    elif command == "--interactive":
        interactive_mode(engine)
    
    else:
        print(f"❌ অজানা কমান্ড: {command}")
        print_help()

if __name__ == "__main__":
    main()
