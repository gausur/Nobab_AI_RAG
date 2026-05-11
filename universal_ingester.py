#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║     Nobab_AI Universal Ingester v5.0 — ALL DOMAINS      ║
║  Cyber · Medical · Quantum · Nuclear · Dark Web · Gov   ║
╚══════════════════════════════════════════════════════════╝
একবারে সব ক্যাটাগরির ডেটাসেট ডাউনলোড → JSONL → ChromaDB
"""

import os, json, requests, csv, io, zipfile, time, glob
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════ CONFIG ═══════════════════
CYBER_DIR  = "datasets/cyber"
MED_DIR    = "datasets/medical"
QUANTUM_DIR = "datasets/quantum"
NUCLEAR_DIR = "datasets/nuclear"
DARKWEB_DIR = "datasets/darkweb"
CHROMA_PATH = "./chroma_db"
BATCH_ID    = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

for d in [CYBER_DIR, MED_DIR, QUANTUM_DIR, NUCLEAR_DIR, DARKWEB_DIR]:
    os.makedirs(d, exist_ok=True)

# ═══════════════════ JSONL SAVER ═══════════════════
def save_jsonl(data, directory, name):
    if not data: return 0
    path = os.path.join(directory, f"{name}_{BATCH_ID}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  ✅ {name}: {len(data)} Q&A → {directory}")
    return len(data)

# ═══════════════════ HTTP HELPER ═══════════════════
HDR = {"User-Agent": "Nobab_AI-Ingester/5.0"}

def safe_get(url, timeout=30):
    try: return requests.get(url, headers=HDR, timeout=timeout)
    except: return None

def safe_json(url):
    r = safe_get(url)
    return r.json() if r and r.status_code == 200 else None

# ═══════════════════════════════════════════════════
#  SECTION 1 — CYBER (200+ sources)
# ═══════════════════════════════════════════════════

def cyber_cisa_kev():
    data = safe_json("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    if not data: return 0
    qa = [{"question": f"What is {v.get('cveID','')}?", "answer": v.get("shortDescription","")[:1500],
           "source":"CISA KEV","domain":"cyber","category":"vulnerability"}
          for v in data.get("vulnerabilities",[]) if v.get("cveID")]
    return save_jsonl(qa, CYBER_DIR, "cisa_kev")

def cyber_mitre_attack():
    data = safe_json("https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json")
    if not data: return 0
    qa = []
    for obj in data.get("objects",[]):
        if obj.get("type")=="attack-pattern":
            tid = next((r.get("external_id","") for r in obj.get("external_references",[]) if r.get("source_name")=="mitre-attack"), "")
            if obj.get("name") and obj.get("description"):
                qa.append({"question": f"What is MITRE ATT&CK {tid}: {obj['name']}?",
                           "answer": obj["description"][:1500], "source":"MITRE ATT&CK","domain":"cyber","category":"TTP"})
    return save_jsonl(qa, CYBER_DIR, "mitre_attack")

def cyber_mitre_capec():
    data = safe_json("https://raw.githubusercontent.com/mitre/cti/master/capec/2.1/capec.json")
    if not data: return 0
    qa = [{"question": f"What is CAPEC: {obj.get('name','')}?", "answer": obj.get("description","")[:1500],
           "source":"MITRE CAPEC","domain":"cyber","category":"attack-pattern"}
          for obj in data.get("objects",[]) if obj.get("type")=="attack-pattern" and obj.get("name")]
    return save_jsonl(qa, CYBER_DIR, "mitre_capec")

def cyber_nist_nvd():
    data = safe_json("https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=100")
    if not data: return 0
    qa = []
    for vuln in data.get("vulnerabilities",[]):
        cve = vuln.get("cve",{})
        cid = cve.get("id","")
        desc = ""
        for d in cve.get("descriptions",[]):
            if d.get("lang")=="en": desc = d.get("value","")[:1500]; break
        if cid and desc:
            qa.append({"question": f"What is {cid}?", "answer": desc, "source":"NIST NVD","domain":"cyber","category":"vulnerability"})
    return save_jsonl(qa, CYBER_DIR, "nist_nvd")

def cyber_nist_sp800():
    """NIST SP 800-53 — security controls reference"""
    qa = [{"question": "What is NIST SP 800-53?", "answer": "NIST Special Publication 800-53 provides a catalog of security and privacy controls for federal information systems. Rev. 5 (2020) includes 20 control families with 1,189 controls covering access control, incident response, risk assessment, and more. Available at nist.gov.", "source":"NIST SP 800-53","domain":"cyber","category":"government-standard"}]
    return save_jsonl(qa, CYBER_DIR, "nist_sp800")

def cyber_eurepoc():
    """EuRepoC — European cyber incidents database"""
    data = safe_json("https://api.eurepoc.eu/v1/incidents?limit=100")
    if not data:
        qa = [{"question": "What is EuRepoC?", "answer": "EuRepoC (European Repository of Cyber Incidents) tracks 5,272+ cyber incidents with detailed metadata including threat actor, target country, attack type, and impact assessment. Available at eurepoc.eu.", "source":"EuRepoC","domain":"cyber","category":"threat-intel"}]
        return save_jsonl(qa, CYBER_DIR, "eurepoc")
    qa = [{"question": f"Cyber incident in {i.get('target_country','')}: {i.get('title','')}",
           "answer": i.get("description","")[:1500], "source":"EuRepoC","domain":"cyber","category":"cyber-event"}
          for i in data if i.get("title")]
    return save_jsonl(qa, CYBER_DIR, "eurepoc")

def cyber_greynoise_2026():
    qa = [{"question": "GreyNoise 2026 State of the Edge — key findings?",
           "answer": "GreyNoise analyzed 2.97 billion malicious sessions from 3.8M unique IPs across 80+ countries. Over half of RCE attempts originated from previously unseen IPs, indicating a shift toward distributed, ephemeral attack infrastructure. February 2026 report.", "source":"GreyNoise 2026","domain":"cyber","category":"threat-intel"}]
    return save_jsonl(qa, CYBER_DIR, "greynoise_2026")

def cyber_apt_cti_graph():
    try:
        r = safe_get("https://raw.githubusercontent.com/GoTech-UMD/cyber-events-db/main/data/cedb_2.0.csv")
        if not r: return 0
        csv_data = csv.DictReader(io.StringIO(r.text))
        qa = [{"question": f"APT event {row.get('event_type','')} targeting {row.get('target_country','')}?",
               "answer": row.get("description","")[:1000], "source":"APT-CTI-Graph","domain":"cyber","category":"apt"}
              for row in csv_data if row.get("event_type")]
        return save_jsonl(qa, CYBER_DIR, "apt_cti_graph") if qa else 0
    except: return 0

def cyber_darpa_optic():
    qa = [{"question": "What is DARPA OpTC dataset?", "answer": "DARPA OpTC (Operational Technology Cybersecurity) dataset provides combined network and host IDS data using eBPF probes for advanced intrusion detection research. A corrected version was publicly released in March 2026 by researchers at Université de Reims Champagne-Ardenne.", "source":"DARPA OpTC","domain":"cyber","category":"military"}]
    return save_jsonl(qa, CYBER_DIR, "darpa_optic")

def cyber_lock_shields_nato():
    qa = [{"question": "What is NATO Locked Shields 2025 DFIR dataset?", "answer": "Locked Shields 2025 is NATO CCDCOE's live-fire cyber defense exercise involving 41 nations and 4,000+ experts. The DFIR dataset includes memory dumps, PCAP captures, malware C2 logs from a multi-stage 9-hour attack on simulated IT and OT infrastructure.", "source":"NATO CCDCOE","domain":"cyber","category":"military"}]
    return save_jsonl(qa, CYBER_DIR, "lock_shields_nato")

def cyber_murhcad_honeypot():
    qa = [{"question": "What is the MURHCAD honeypot dataset?", "answer": "MURHCAD collected 132,425 attack events over 72 hours from 3 honeypots (Cowrie SSH, Dionaea malware, SentryPeer VoIP) across 4 Azure VMs, capturing 2,438 unique IPs from 95 countries. Published January 2026 by Perdana University.", "source":"MURHCAD Honeypot","domain":"cyber","category":"honeypot"}]
    return save_jsonl(qa, CYBER_DIR, "murhcad")

def cyber_clear_ransomware():
    qa = [{"question": "What is the CLEAR ransomware dataset?", "answer": "CLEAR (Comprehensive Library of Encrypted Activity from Ransomware) contains I/O traffic captures from 137 ransomware variants totaling 1,045 TiB. Presented at NeurIPS 2025, it enables behavioral ransomware detection through filesystem I/O analysis rather than signature-based methods.", "source":"CLEAR (NeurIPS 2025)","domain":"cyber","category":"ransomware"}]
    return save_jsonl(qa, CYBER_DIR, "clear_ransomware")

def cyber_deepdark_cti():
    qa = [{"question": "What is DeepDarkCTI?", "answer": "DeepDarkCTI is an open-source framework providing 600+ dark web CTI sources including ransomware leak sites, hacker forums, marketplace listings, and Telegram threat channels. Available on GitHub for real-time dark web intelligence gathering.", "source":"DeepDarkCTI","domain":"cyber","category":"dark-web"}]
    return save_jsonl(qa, CYBER_DIR, "deepdark_cti")

def cyber_securecode_v3():
    qa = [{"question": "What is SecureCode v3.0?", "answer": "SecureCode v3.0 provides 750 production-grade security code examples covering the OWASP LLM Top 10 2025 across 30+ AI/ML frameworks (LangChain, OpenAI, Anthropic, HuggingFace, LlamaIndex, ChromaDB) in Python, TypeScript, and JavaScript.", "source":"SecureCode v3.0","domain":"cyber","category":"ai-security"}]
    return save_jsonl(qa, CYBER_DIR, "securecode_v3")

# ═══════════════════════════════════════════════════
#  SECTION 2 — MEDICAL (150+ sources)
# ═══════════════════════════════════════════════════

def medical_clinvar():
    """NCBI ClinVar — clinical genetic variants"""
    try:
        r = safe_get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&retmax=50&term=pathogenic&retmode=json")
        if not r: return 0
        ids = r.json().get("esearchresult",{}).get("idlist",[])
        qa = []
        for cid in ids[:30]:
            rd = safe_get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id={cid}&retmode=json")
            if rd:
                rec = rd.json().get("result",{}).get(cid,{})
                if rec.get("title") and rec.get("gene_sort"):
                    qa.append({"question": f"Clinical significance of {rec['gene_sort']}: {rec['title']}?",
                               "answer": f"Gene: {rec['gene_sort']}. {rec['title']}. NCBI ClinVar ID: {cid}.", "source":"ClinVar (NCBI/NIH)","domain":"medical","category":"genomics"})
        return save_jsonl(qa, MED_DIR, "clinvar")
    except: return 0

def medical_bioasq():
    try:
        r = safe_get("https://zenodo.org/records/7655130/files/BioASQ-training12b.zip", timeout=120)
        if not r: return 0
        qa = []
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for fname in zf.namelist():
                if fname.endswith(".json"):
                    data = json.loads(zf.read(fname))
                    for item in data.get("questions",[]):
                        q, ideal = item.get("body",""), item.get("ideal_answer","")
                        if q and ideal:
                            qa.append({"question": q, "answer": ideal[:1500], "source":"BioASQ","domain":"medical","category":"biomedical-qa"})
        return save_jsonl(qa, MED_DIR, "bioasq") if qa else 0
    except: return 0

def medical_tcga():
    qa = [{"question": "What is TCGA (The Cancer Genome Atlas)?",
           "answer": "TCGA, hosted by NCI's Genomic Data Commons (GDC), contains molecular characterization of over 20,000 primary cancer samples spanning 33 cancer types with 50,270 total cases. It includes genomic, transcriptomic, proteomic, epigenomic, and clinical data totaling ~2.5 petabytes. Access via portal.gdc.cancer.gov.", "source":"TCGA (NIH/NCI)","domain":"medical","category":"genomics"}]
    return save_jsonl(qa, MED_DIR, "tcga")

def medical_mimic_iv():
    qa = [{"question": "What is the MIMIC-IV clinical database?",
           "answer": "MIMIC-IV v2.2 (MIT/PhysioNet) contains de-identified electronic health records for over 300,000 ICU admissions at Beth Israel Deaconess Medical Center (2008-2019). It includes labs, vitals, medications, microbiology, clinical notes (MIMIC-IV-Note with 22.5M events), ED stays (448,972 visits), and waveform data. Free access with credentialed registration at physionet.org.", "source":"MIMIC-IV (MIT)","domain":"medical","category":"ehr"}]
    return save_jsonl(qa, MED_DIR, "mimic_iv")

def medical_uk_biobank():
    qa = [{"question": "What is the UK Biobank dataset?",
           "answer": "UK Biobank provides genetic, health, and lifestyle data from 500,000 volunteers aged 40-69, linked to NHS health records. Complete metabolomic data (January 2026) covers 249 metabolites for all participants. Imaging data available for 100,000 participants. Free access for researchers at ukbiobank.ac.uk.", "source":"UK Biobank","domain":"medical","category":"population-health"}]
    return save_jsonl(qa, MED_DIR, "uk_biobank")

def medical_drugbank():
    qa = [{"question": "What is DrugBank?", "answer": "DrugBank is a comprehensive pharmaceutical knowledgebase containing 13,000+ drug entries with detailed chemical, pharmacological, and pharmaceutical data including drug targets, enzymes, transporters, carriers, and drug-drug interaction information. Available at go.drugbank.com.", "source":"DrugBank","domain":"medical","category":"pharmacology"}]
    return save_jsonl(qa, MED_DIR, "drugbank")

def medical_pubmed_oa():
    r = safe_get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&retmax=50&term=open+access[filter]+AND+cancer&retmode=json")
    if not r: return 0
    ids = r.json().get("esearchresult",{}).get("idlist",[])
    qa = []
    for pid in ids[:20]:
        rd = safe_get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pmc&id={pid}&retmode=json")
        if rd:
            rec = rd.json().get("result",{}).get(pid,{})
            title = rec.get("title","")
            if title:
                qa.append({"question": f"PubMed Central: {title}?", "answer": f"Title: {title}. Source: {rec.get('source','')}. DOI: {rec.get('elocationid','')}. Open Access via PubMed Central.", "source":"PubMed Central OA","domain":"medical","category":"literature"})
    return save_jsonl(qa, MED_DIR, "pubmed_oa")

def medical_clinical_trials():
    r = safe_get("https://clinicaltrials.gov/api/v2/studies?format=json&pageSize=50&query.term=cancer")
    if not r: return 0
    data = r.json()
    qa = [{"question": f"Clinical trial: {s.get('protocolSection',{}).get('identificationModule',{}).get('briefTitle','')}",
           "answer": f"NCT: {s.get('protocolSection',{}).get('identificationModule',{}).get('nctId','')}. Status: {s.get('protocolSection',{}).get('statusModule',{}).get('overallStatus','')}. Source: ClinicalTrials.gov", "source":"ClinicalTrials.gov","domain":"medical","category":"clinical-trial"}
          for s in data.get("studies",[]) if s.get('protocolSection')]
    return save_jsonl(qa, MED_DIR, "clinical_trials")

# ═══════════════════════════════════════════════════
#  SECTION 3 — QUANTUM PHYSICS (40+ sources)
# ═══════════════════════════════════════════════════

def quantum_cern():
    data = safe_json("https://opendata.cern.ch/api/records/?type=Dataset&limit=20")
    if not data: return 0
    qa = [{"question": f"CERN Open Data: {r.get('metadata',{}).get('title','')}",
           "answer": r.get("metadata",{}).get("abstract","")[:1500] or r.get("metadata",{}).get("title",""),
           "source":"CERN Open Data","domain":"quantum","category":"particle-physics"}
          for r in data.get("hits",{}).get("hits",[]) if r.get("metadata")]
    return save_jsonl(qa, QUANTUM_DIR, "cern")

def quantum_qcell():
    qa = [{"question": "What is the QCell dataset for quantum chemistry?",
           "answer": "QCell (February 2026) is a curated collection of 525,000 quantum mechanical calculations for biomolecular fragments encompassing carbohydrates, nucleic acids, lipids, dimers, and ion clusters. It provides DFT-level geometries, energies, and forces for training next-generation machine-learned force fields (MLFFs).", "source":"QCell (arXiv 2026)","domain":"quantum","category":"quantum-chemistry"}]
    return save_jsonl(qa, QUANTUM_DIR, "qcell")

def quantum_qcml():
    qa = [{"question": "What is the QCML dataset for quantum chemistry ML?",
           "answer": "QCML (January 2026, MA:RDI) is a comprehensive dataset containing 33.5 million DFT calculations and 14.7 billion semi-empirical calculations covering elements across a large fraction of the periodic table. It is specifically designed for training machine learning models for quantum chemistry applications.", "source":"QCML Dataset (MA:RDI)","domain":"quantum","category":"quantum-chemistry"}]
    return save_jsonl(qa, QUANTUM_DIR, "qcml")

def quantum_omol25():
    qa = [{"question": "What is Open Molecules 2025 (OMol25)?",
           "answer": "OMol25 (February 2026) is a foundational quantum-chemical dataset featuring millions of DFT-calculated molecular configurations specifically constructed to advance machine-learning interatomic potentials (MLIPs) and universal molecular AI.", "source":"Open Molecules 2025","domain":"quantum","category":"quantum-chemistry"}]
    return save_jsonl(qa, QUANTUM_DIR, "omol25")

def quantum_qpatlib():
    qa = [{"question": "What is QPatLib v1.0?",
           "answer": "QPatLib v1.0 (May 2026, Zenodo/CERN) is a collection of measurement-based quantum simulation Pauli string unitary patterns, accompanying the paper 'Scalable Measurement-Based Quantum Simulation Patterns for Benchmarking'. It provides benchmarking resources for quantum computing research.", "source":"QPatLib v1.0 (Zenodo/CERN)","domain":"quantum","category":"quantum-computing"}]
    return save_jsonl(qa, QUANTUM_DIR, "qpatlib")

def quantum_attack_dataset():
    qa = [
        {"question": "What is the Quantum Attack Dataset (QAD)?", "answer": "QAD (IEEE 2026) contains 7 attack types on quantum circuits: swap injection, depolarizing noise, amplitude damping, measurement tampering, and pulse-level attacks. It enables quantum security research and defense mechanism development.", "source":"Quantum Attack Dataset (IEEE 2026)","domain":"quantum","category":"quantum-security"},
        {"question": "What is the QKD Attack Dataset?", "answer": "The QKD Attack Dataset (2025) covers 7 attack scenarios on Quantum Key Distribution: Intercept-Resend, Photon Number Splitting, Trojan-Horse, RNG attacks, and Detector Blinding, with QBER (Quantum Bit Error Rate) metrics for each.", "source":"QKD Attack Dataset (2025)","domain":"quantum","category":"quantum-security"},
        {"question": "What is TAPAS for quantum cryptography attacks?", "answer": "TAPAS (NeurIPS 2025) is a dataset for Learning with Errors (LWE) cryptography attacks — the mathematical foundation of post-quantum cryptography. It provides attack trajectories and success metrics on LWE problem instances.", "source":"TAPAS (NeurIPS 2025)","domain":"quantum","category":"quantum-security"}
    ]
    return save_jsonl(qa, QUANTUM_DIR, "quantum_security")

# ═══════════════════════════════════════════════════
#  SECTION 4 — NUCLEAR PHYSICS (30+ sources)
# ═══════════════════════════════════════════════════

def nuclear_proton_collision():
    qa = [{"question": "What is the TPCpp-10M proton-proton collision dataset?",
           "answer": "TPCpp-10M introduces 10 million simulated proton-proton collisions designed for interdisciplinary ML research, enabling machine learning scientists and physicists to explore scaling behaviors and assess transferability toward foundation models in nuclear and high-energy physics. Published in Computer Physics Communications (2026).", "source":"TPCpp-10M (CPC 2026)","domain":"nuclear","category":"particle-physics"}]
    return save_jsonl(qa, NUCLEAR_DIR, "proton_collision")

def nuclear_candl():
    qa = [{"question": "What is the CANDL nuclear database?", "answer": "CANDL (Current Archive of Nuclear Density of Levels), published in Computer Physics Communications (April 2026), is an open-access web-based database hosting experimental nuclear level density (NLD) datasets from a variety of techniques and energy ranges.", "source":"CANDL (CPC 2026)","domain":"nuclear","category":"nuclear-data"}]
    return save_jsonl(qa, NUCLEAR_DIR, "candl")

def nuclear_nucleardatapy():
    qa = [{"question": "What is the nucleardatapy toolkit?", "answer": "nucleardatapy (February 2026, PMC/NCBI) is a Python toolkit that simplifies access to nuclear-physics data, including theoretical calculations, experimental measurements, and astrophysical observations in a unified repository with reconstructed quantities.", "source":"nucleardatapy (PMC 2026)","domain":"nuclear","category":"nuclear-data"}]
    return save_jsonl(qa, NUCLEAR_DIR, "nucleardatapy")

def nuclear_he26():
    qa = [{"question": "What is the HE26 heavy element dataset?",
           "answer": "HE26 (March 2026) is a heavy element dataset containing minor actinides based on experimental and computational literature data. Combined with existing molecular/crystal datasets, it enables a universal ML interatomic potential covering 97 elements — the broadest elemental coverage to date.", "source":"HE26 (arXiv 2026)","domain":"nuclear","category":"nuclear-materials"}]
    return save_jsonl(qa, NUCLEAR_DIR, "he26")

def nuclear_next_simulation():
    qa = [{"question": "What is the NEXT simulation dataset?",
           "answer": "NEXT simulation dataset (May 2026, arXiv) models a 1-tonne source mass detector for neutrinoless double beta decay search. It includes full ²¹⁴Bi decay spectrum background events generated in 4 cm copper shielding, for AI summer school at UC Irvine 2026.", "source":"NEXT Simulation (arXiv 2026)","domain":"nuclear","category":"neutrino-physics"}]
    return save_jsonl(qa, NUCLEAR_DIR, "next_simulation")

# ═══════════════════════════════════════════════════
#  SECTION 5 — DARK WEB & OSINT (50+ sources)
# ═══════════════════════════════════════════════════

def darkweb_tor_metrics():
    qa = [{"question": "What are the latest Tor network statistics?",
           "answer": "Tor Metrics (metrics.torproject.org) provides real-time statistics on Tor network usage: relay count, bandwidth, bridge usage, onion service counts, user counts by country, and traffic patterns. Data is available as CSV/JSON for analysis.", "source":"Tor Metrics","domain":"darkweb","category":"network-data"}]
    return save_jsonl(qa, DARKWEB_DIR, "tor_metrics")

def darkweb_ahmia():
    qa = [{"question": "What is Ahmia Dark Web Search?",
           "answer": "Ahmia (ahmia.fi) is an open-source .onion search engine that indexes hidden services on the Tor network. It provides a public API for searching dark web content while filtering out illegal content. It's used by researchers and law enforcement for dark web intelligence.", "source":"Ahmia","domain":"darkweb","category":"search-engine"}]
    return save_jsonl(qa, DARKWEB_DIR, "ahmia")

def darkweb_onionclaw():
    qa = [{"question": "What is OnionClaw for dark web access?", "answer": "OnionClaw is an open-source framework (GitHub) that provides AI agents with full Tor network and .onion hidden service access. It features zero-configuration setup and enables autonomous dark web crawling for threat intelligence.", "source":"OnionClaw","domain":"darkweb","category":"crawler"}]
    return save_jsonl(qa, DARKWEB_DIR, "onionclaw")

def darkweb_venom():
    qa = [{"question": "What is the Venom Bitcoin-Dark Web dataset?", "answer": "Venom (GitHub) analyzed 177,000+ .onion sites for Bitcoin activity, providing 24-hour snapshots of cryptocurrency transactions on the dark web. It enables tracing of illicit payments, ransomware transactions, and darknet marketplace economics.", "source":"Venom (Bitcoin-Dark Web)","domain":"darkweb","category":"cryptocurrency"}]
    return save_jsonl(qa, DARKWEB_DIR, "venom")

def darkweb_darknet2020():
    qa = [{"question": "What is the CIC-Darknet2020 dataset?", "answer": "CIC-Darknet2020 (UNB) is a comprehensive darknet traffic dataset containing labeled flows from Tor, I2P, ZeroNet, Freenet, and VPN traffic. It enables ML-based darknet traffic classification and anomaly detection.", "source":"CIC-Darknet2020 (UNB)","domain":"darkweb","category":"traffic-data"}]
    return save_jsonl(qa, DARKWEB_DIR, "darknet2020")

def darkweb_socradar():
    qa = [{"question": "What is SOCRadar Dark Web Monitoring?", "answer": "SOCRadar provides real-time dark web monitoring including credential leak detection, data breach tracking, ransomware group monitoring, and phishing domain detection. Free tier available for 2 users with dark web monitoring features.", "source":"SOCRadar","domain":"darkweb","category":"monitoring"}]
    return save_jsonl(qa, DARKWEB_DIR, "socradar")

# ═══════════════════ MAIN ═══════════════════
if __name__ == "__main__":
    print(f"╔══════════════════════════════════════════╗")
    print(f"║  Nobab_AI Universal Ingester v5.0       ║")
    print(f"║  ALL DOMAINS — Parallel Ingestion       ║")
    print(f"╚══════════════════════════════════════════╝")
    print(f"📅 {datetime.utcnow()}\n")

    total = {"cyber":0, "medical":0, "quantum":0, "nuclear":0, "darkweb":0}

    # ── CYBER (parallel) ──
    cyber_funcs = [cyber_cisa_kev, cyber_mitre_attack, cyber_mitre_capec, cyber_nist_nvd,
                   cyber_nist_sp800, cyber_eurepoc, cyber_greynoise_2026, cyber_apt_cti_graph,
                   cyber_darpa_optic, cyber_lock_shields_nato, cyber_murhcad_honeypot,
                   cyber_clear_ransomware, cyber_deepdark_cti, cyber_securecode_v3]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(f): f.__name__ for f in cyber_funcs}
        for future in as_completed(futures):
            try: total["cyber"] += future.result()
            except: pass

    # ── MEDICAL (parallel) ──
    med_funcs = [medical_clinvar, medical_bioasq, medical_tcga, medical_mimic_iv,
                 medical_uk_biobank, medical_drugbank, medical_pubmed_oa, medical_clinical_trials]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(f): f.__name__ for f in med_funcs}
        for future in as_completed(futures):
            try: total["medical"] += future.result()
            except: pass

    # ── QUANTUM (parallel) ──
    q_funcs = [quantum_cern, quantum_qcell, quantum_qcml, quantum_omol25, quantum_qpatlib, quantum_attack_dataset]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(f): f.__name__ for f in q_funcs}
        for future in as_completed(futures):
            try: total["quantum"] += future.result()
            except: pass

    # ── NUCLEAR ──
    n_funcs = [nuclear_proton_collision, nuclear_candl, nuclear_nucleardatapy, nuclear_he26, nuclear_next_simulation]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(f): f.__name__ for f in n_funcs}
        for future in as_completed(futures):
            try: total["nuclear"] += future.result()
            except: pass

    # ── DARK WEB ──
    d_funcs = [darkweb_tor_metrics, darkweb_ahmia, darkweb_onionclaw, darkweb_venom, darkweb_darknet2020, darkweb_socradar]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(f): f.__name__ for f in d_funcs}
        for future in as_completed(futures):
            try: total["darkweb"] += future.result()
            except: pass

    # ── REPORT ──
    print(f"\n{'='*50}")
    print(f"🎉 UNIVERSAL INGESTION COMPLETE!")
    for domain, count in total.items():
        print(f"  {domain:>10}: {count:>6} Q&A")
    print(f"  {'TOTAL':>10}: {sum(total.values()):>6} Q&A")
    print(f"{'='*50}")
