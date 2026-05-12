# human_fetcher.py (সরল সংস্করণ – শুধু GenBank)
import os
import json
import gzip
import ftplib
from tqdm import tqdm
from human_config import HUMAN_DATA_ROOT, SAMPLE_LIMIT

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
    print(f"Saved to {out_file}")

if __name__ == "__main__":
    fetch_genbank()
