# human_indexer.py
import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from human_config import HUMAN_CHROMA_DIR, HUMAN_COLLECTION, HUMAN_DATA_ROOT

embedder = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path=HUMAN_CHROMA_DIR)

try:
    client.delete_collection(HUMAN_COLLECTION)
except:
    pass
collection = client.create_collection(name=HUMAN_COLLECTION)

def index_jsonl(file_path, source_name):
    if not os.path.exists(file_path):
        print(f"{file_path} not found, skipping.")
        return
    with open(file_path, "r") as f:
        records = [json.loads(line) for line in f if line.strip()]
    if not records:
        return
    ids = [f"{source_name}_{i}" for i in range(len(records))]
    texts = [r["text"] for r in records]
    metadatas = [{"source": r["source"], "type": r["type"], "id": r["id"]} for r in records]
    embeddings = embedder.encode(texts).tolist()
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    print(f"Indexed {len(records)} records from {source_name}")

if __name__ == "__main__":
    for jsonl_file in ["genbank.jsonl", "pdb.jsonl", "pubchem.jsonl", "string.jsonl"]:
        full_path = os.path.join(HUMAN_DATA_ROOT, jsonl_file)
        index_jsonl(full_path, jsonl_file.replace(".jsonl", ""))
    print(f"Indexing complete. Collection size: {collection.count()}")
