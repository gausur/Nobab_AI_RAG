# human_fetcher.py
import os
import json
import gzip
import ftplib
import requests
from tqdm import tqdm
from human_config import HUMAN_DATA_ROOT, SAMPLE_LIMIT

os.makedirs(HUMAN_DATA_ROOT, exist_ok=True)

# ------------------- GenBank -------------------
def fetch_genbank():
    out = os.path.join(HUMAN_DATA_ROOT, "genbank.jsonl")
    ftp = ftplib.FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/genbank")
    files = ftp.nlst("*.seq.gz")[:SAMPLE_LIMIT]
    with open(out, "w") as f:
        for name in tqdm(files, desc="GenBank"):
            local = name
            with open(local, "wb") as lf:
                ftp.retrbinary(f"RETR {name}", lf.write)
            with gzip.open(local, "rt") as gz:
                txt = gz.read(1500)
            rec = {"source": "genbank", "id": name, "text": txt, "type": "dna"}
            f.write(json.dumps(rec) + "\n")
            os.remove(local)
    ftp.quit()

# ------------------- PDB -------------------
def fetch_pdb():
    out = os.path.join(HUMAN_DATA_ROOT, "pdb.jsonl")
    # Real PDB IDs sample (first 10 from a valid list)
    pdb_ids = ["1l2y", "2gc4", "3fx2", "4hhb", "5p21", "6lu7", "7kdf", "8abc", "9ins", "10gs"]
    with open(out, "w") as f:
        for pid in tqdm(pdb_ids[:SAMPLE_LIMIT], desc="PDB"):
            url = f"https://files.rcsb.org/download/{pid}.cif"
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    rec = {"source": "pdb", "id": pid, "text": r.text[:1500], "type": "protein"}
                    f.write(json.dumps(rec) + "\n")
            except:
                continue

# ------------------- PubChem -------------------
def fetch_pubchem():
    out = os.path.join(HUMAN_DATA_ROOT, "pubchem.jsonl")
    # Use FTP with correct current path
    ftp = ftplib.FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    try:
        ftp.cwd("/pubchem/Compound/CURRENT-Full/SDF")
        files = [f for f in ftp.nlst() if f.endswith(".sdf.gz")][:SAMPLE_LIMIT]
        with open(out, "w") as f:
            for fname in tqdm(files, desc="PubChem"):
                local = fname
                with open(local, "wb") as lf:
                    ftp.retrbinary(f"RETR {fname}", lf.write)
                with gzip.open(local, "rt") as gz:
                    data = gz.read(1500)
                rec = {"source": "pubchem", "id": fname, "text": data, "type": "molecule"}
                f.write(json.dumps(rec) + "\n")
                os.remove(local)
    except Exception as e:
        print(f"PubChem FTP error: {e}")
    finally:
        ftp.quit()

# ------------------- STRING (small sample) -------------------
def fetch_string():
    out = os.path.join(HUMAN_DATA_ROOT, "string.jsonl")
    url = "https://string-db.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz"
    local_gz = os.path.join(HUMAN_DATA_ROOT, "string_temp.gz")
    try:
        r = requests.get(url, stream=True)
        with open(local_gz, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        with gzip.open(local_gz, "rt") as gz:
            lines = gz.readlines()[:SAMPLE_LIMIT*5]
        with open(out, "w") as f:
            for line in lines[1:SAMPLE_LIMIT+1]:
                parts = line.strip().split()
                if len(parts) >= 3:
                    txt = f"Protein {parts[0]} interacts with {parts[1]} score {parts[2]}"
                    rec = {"source": "string", "id": f"{parts[0]}_{parts[1]}", "text": txt, "type": "ppi"}
                    f.write(json.dumps(rec) + "\n")
    except Exception as e:
        print(f"STRING error: {e}")
    finally:
        if os.path.exists(local_gz):
            os.remove(local_gz)

# ------------------- RNAcentral -------------------
def fetch_rnacentral():
    out = os.path.join(HUMAN_DATA_ROOT, "rnacentral.jsonl")
    ftp = ftplib.FTP("ftp.ebi.ac.uk")
    ftp.login()
    ftp.cwd("/pub/databases/RNAcentral/current_release/id_mapping/")
    files = [f for f in ftp.nlst() if f.endswith(".txt.gz")][:SAMPLE_LIMIT]
    with open(out, "w") as f:
        for fname in tqdm(files, desc="RNAcentral"):
            local = fname
            with open(local, "wb") as lf:
                ftp.retrbinary(f"RETR {fname}", lf.write)
            with gzip.open(local, "rt") as gz:
                data = gz.read(1500)
            rec = {"source": "rnacentral", "id": fname, "text": data, "type": "rna"}
            f.write(json.dumps(rec) + "\n")
            os.remove(local)
    ftp.quit()

# ------------------- Main -------------------
if __name__ == "__main__":
    print("Fetching all sources...")
    fetch_genbank()
    fetch_pdb()
    fetch_pubchem()
    fetch_string()
    fetch_rnacentral()
    print("All done! Files saved in", HUMAN_DATA_ROOT)
