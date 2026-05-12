# human_config.py
import os

HUMAN_CHROMA_DIR = "./chroma_human_db"
HUMAN_COLLECTION = "human_particle_knowledge"

DEEPSEEK_API_BASE = "http://localhost:8000/v1"   # আপনার DeepSeek এন্ডপয়েন্ট
DEEPSEEK_API_KEY = "your-api-key"

HUMAN_DATA_ROOT = "./datasets/human_particle"
os.makedirs(HUMAN_DATA_ROOT, exist_ok=True)

SOURCES = {
    "genbank": "ftp://ftp.ncbi.nlm.nih.gov/genbank/",
    "pdb": "ftp://ftp.wwpdb.org/pub/pdb/data/structures/divided/mmCIF/",
    "pubchem": "ftp://ftp.ncbi.nlm.nih.gov/pubchem/Compound/MOL/",
    "string": "https://string-db.org/download/",
    "rnacentral": "ftp://ftp.ebi.ac.uk/pub/databases/RNAcentral/"
}

SAMPLE_LIMIT = 10   # পূর্ণ ডেটার জন্য বড় সংখ্যা দিন
