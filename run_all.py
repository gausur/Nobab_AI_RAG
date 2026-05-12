# run_all.py
import subprocess
import sys

steps = [
    ("python human_fetcher.py", "ডেটা ফেচ করছে..."),
    ("python human_indexer.py", "ChromaDB তে ইনডেক্স করছে..."),
    ("python human_rag.py", "RAG চালু হচ্ছে (প্রশ্ন করতে পারো)...")
]

for cmd, msg in steps:
    print(msg)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error in {cmd}")
        sys.exit(1)
