#!/usr/bin/env python3
"""
Incremental Indexer — শুধু নতুন JSONL ফাইল ChromaDB-তে যোগ করবে
"""

import os, json, glob, time, chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "./chroma_db"
TRACKER_FILE = "indexed_files.json"
DOMAINS = {
    "cyber": {
        "collection": "cyber_defender",
        "dataset_dir": "datasets/cyber"
    },
    "medical": {
        "collection": "medical_knowledge",
        "dataset_dir": "datasets/medical"
    }
}

# 1. ট্র্যাকার লোড (কোন কোন ফাইল ইনডেক্স হয়েছে)
def load_tracker():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    return {"cyber": [], "medical": []}

# 2. ট্র্যাকার সেভ
def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)

# 3. ChromaDB ক্লায়েন্ট
client = chromadb.PersistentClient(path=CHROMA_PATH)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# 4. JSONL থেকে Q&A লোড
def load_jsonl_file(file_path):
    docs, ids, metas = [], [], []
    fname = os.path.basename(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
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
                    ids.append(f"{fname}_{i}_{int(time.time())}")
                    metas.append({"source": src, "file": fname})
            except json.JSONDecodeError:
                continue
    return docs, ids, metas

# 5. মেইন লজিক
def incremental_index():
    tracker = load_tracker()
    total_new = 0

    for domain, cfg in DOMAINS.items():
        collection = client.get_or_create_collection(
            name=cfg["collection"],
            embedding_function=ef
        )
        pattern = os.path.join(cfg["dataset_dir"], "*.jsonl")
        all_files = sorted(glob.glob(pattern))
        indexed = set(tracker[domain])
        new_files = [f for f in all_files if os.path.basename(f) not in indexed]

        if not new_files:
            print(f"ℹ️ {domain}: কোনো নতুন ফাইল নেই")
            continue

        print(f"🆕 {domain}: {len(new_files)}টি নতুন ফাইল পাওয়া গেছে")
        for file_path in new_files:
            docs, ids, metas = load_jsonl_file(file_path)
            if docs:
                for i in range(0, len(docs), 100):
                    collection.add(
                        documents=docs[i:i+100],
                        ids=ids[i:i+100],
                        metadatas=metas[i:i+100]
                    )
                total_new += len(docs)
                print(f"  ✅ {os.path.basename(file_path)}: {len(docs)} ডকুমেন্ট")

            # ট্র্যাকারে যুক্ত করো
            tracker[domain].append(os.path.basename(file_path))

    if total_new > 0:
        save_tracker(tracker)
        print(f"🎉 মোট {total_new}টি নতুন ডকুমেন্ট ইনডেক্স হয়েছে")
    else:
        print("ℹ️ কোনো নতুন ডকুমেন্ট নেই")

if __name__ == "__main__":
    incremental_index()
