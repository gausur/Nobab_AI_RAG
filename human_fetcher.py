# human_fetcher.py
import os
import json
import gzip
import ftplib
import requests
from tqdm import tqdm
from human_config import HUMAN_DATA_ROOT, SOURCES, SAMPLE_LIMIT

def fetch_genbank():
    out_file = os.path.join(HUMAN_DATA_ROOT, "genbank.jsonl")
    ftp = ftplib.FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/genbank")
    files = ftp.nlst("*.seq.gz")[:SAMPLE_LIMIT]
    with open(out_file, "w") as out:
        for fname in tqdm(files, desc="GenBank"):
            local = os.path.join(HUMAN_DATA_ROOT, fname)
            with open(local, "wb") as lf:
                ftp.retrbinary(f"RETR {fname}", lf.write)
            with gzip.open(local, "rt") as gz:
                data = gz.read(1500)
            rec = {"source": "genbank", "id": fname, "text": data, "type": "dna"}
            out.write(json.dumps(rec) + "\n")
            os.remove(local)
    ftp.quit()

def fetch_pdb():
    out_file = os.path.join(HUMAN_DATA_ROOT, "pdb.jsonl")
    base = "https://files.rcsb.org/download/"
    with open(out_file, "w") as out:
        for i in range(1, SAMPLE_LIMIT+1):
            pdb_id = f"{i:04d}"
            url = base + pdb_id + ".cif"
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    rec = {"source": "pdb", "id": pdb_id, "text": r.text[:1500], "type": "protein"}
                    out.write(json.dumps(rec) + "\n")
            except:
                continue

def fetch_pubchem():
    out_file = os.path.join(HUMAN_DATA_ROOT, "pubchem.jsonl")
    ftp = ftplib.FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/pubchem/Compound/MOL")
    files = ftp.nlst("*.sdf.gz")[:SAMPLE_LIMIT]
    with open(out_file, "w") as out:
        for fname in tqdm(files, desc="PubChem"):
            local = os.path.join(HUMAN_DATA_ROOT, fname)
            with open(local, "wb") as lf:
                ftp.retrbinary(f"RETR {fname}", lf.write)
            with gzip.open(local, "rt") as gz:
                content = gz.read(1500)
            rec = {"source": "pubchem", "id": fname, "text": content, "type": "molecule"}
            out.write(json.dumps(rec) + "\n")
            os.remove(local)
    ftp.quit()

def fetch_string():
    out_file = os.path.join(HUMAN_DATA_ROOT, "string.jsonl")
    url = "https://string-db.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz"
    local_gz = os.path.join(HUMAN_DATA_ROOT, "string_sample.txt.gz")
    response = requests.get(url, stream=True)
    with open(local_gz, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    with gzip.open(local_gz, "rt") as gz:
        lines = gz.readlines()[:SAMPLE_LIMIT*10]
    with open(out_file, "w") as out:
        for line in lines[1:SAMPLE_LIMIT+1]:
            parts = line.strip().split()
            if len(parts) >= 3:
                rec = {"source": "string", "id": f"{parts[0]}_{parts[1]}",
                       "text": f"Protein {parts[0]} interacts with {parts[1]} with score {parts[2]}",
                       "type": "ppi"}
                out.write(json.dumps(rec) + "\n")
    os.remove(local_gz)

if __name__ == "__main__":
    print("Fetching GenBank...")
    fetch_genbank()
    print("Fetching PDB...")
    fetch_pdb()
    print("Fetching PubChem...")
    fetch_pubchem()
    print("Fetching STRING...")
    fetch_string()
    print("All done! JSONL files saved in", HUMAN_DATA_ROOT)
