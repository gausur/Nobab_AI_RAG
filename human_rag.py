# human_rag.py
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from human_config import HUMAN_CHROMA_DIR, HUMAN_COLLECTION, DEEPSEEK_API_BASE, DEEPSEEK_API_KEY

embedder = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path=HUMAN_CHROMA_DIR)
collection = client.get_collection(HUMAN_COLLECTION)

deep_client = OpenAI(base_url=DEEPSEEK_API_BASE, api_key=DEEPSEEK_API_KEY)

def ask(query, top_k=5):
    q_emb = embedder.encode([query]).tolist()
    results = collection.query(query_embeddings=q_emb, n_results=top_k)
    docs = results['documents'][0]
    sources = [m['source'] for m in results['metadatas'][0]]
    
    context = "\n\n".join(docs)
    prompt = f"""তুমি একজন জৈব-আণবিক ও ন্যানো প্রযুক্তি বিশেষজ্ঞ। নিচের তথ্যের ভিত্তিতে প্রশ্নের উত্তর দাও।

তথ্য:
{context}

প্রশ্ন: {query}

উত্তর (বাংলায়, বিস্তারিত):"""
    
    response = deep_client.chat.completions.create(
        model="deepseek-r1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    answer = response.choices[0].message.content
    return answer, sources

if __name__ == "__main__":
    while True:
        q = input("\nতোমার প্রশ্ন (হিউম্যান পার্টিকেল সম্পর্কে): ")
        if q.lower() in ["exit", "quit"]:
            break
        ans, src = ask(q)
        print("\nউত্তর:", ans)
        print("\nউৎস:", src)
