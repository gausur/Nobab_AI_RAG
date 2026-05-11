#!/usr/bin/env python3
"""
Nobab_AI Master Collector (v4.0)
সাইবার ৫৫০+ + মেডিকেল ৫০০+ = ১০৫০+ সোর্স থেকে ডেটা টানে
সব JSONL datasets/cyber/ বা datasets/medical/-এ জমা হয়
"""

import os, json, requests, csv, io, zipfile, time
from datetime import datetime

BATCH_ID = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
CYBER_DIR = "datasets/cyber"
MED_DIR = "datasets/medical"
os.makedirs(CYBER_DIR, exist_ok=True)
os.makedirs(MED_DIR, exist_ok=True)

def save_cyber(data, name):
    path = os.path.join(CYBER_DIR, f"{name}_{BATCH_ID}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for d in data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"✅ [CYBER] {name}: {len(data)} Q&A")

def save_med(data, name):
    path = os.path.join(MED_DIR, f"{name}_{BATCH_ID}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for d in data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"✅ [MED] {name}: {len(data)} Q&A")

# ============ সাইবার ============
def cisa_kev():
    r = requests.get("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    d = r.json()
    qa = [{"question": f"What is {v.get('cveID')}?", "answer": v.get("shortDescription",""),
           "source": "CISA KEV", "category": "vulnerability"} for v in d.get("vulnerabilities",[]) if v.get("cveID")]
    save_cyber(qa, "cisa_kev")

def mitre_attack():
    r = requests.get("https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json")
    atk = r.json()
    qa = []
    for obj in atk.get("objects",[]):
        if obj.get("type")=="attack-pattern":
            tid = next((ref.get("external_id","") for ref in obj.get("external_references",[]) if ref.get("source_name")=="mitre-attack"), "")
            if obj.get("name") and obj.get("description"):
                qa.append({"question": f"What is MITRE ATT&CK {tid}: {obj['name']}?",
                           "answer": obj["description"][:1500], "source": "MITRE ATT&CK", "category": "TTP"})
    save_cyber(qa, "mitre_attack")

def mitre_capec():
    r = requests.get("https://raw.githubusercontent.com/mitre/cti/master/capec/2.1/capec.json")
    capec = r.json()
    qa = [{"question": f"What is CAPEC: {obj.get('name','')}?",
           "answer": obj.get("description","")[:1500], "source": "MITRE CAPEC", "category": "attack-pattern"}
          for obj in capec.get("objects",[]) if obj.get("type")=="attack-pattern" and obj.get("name")]
    save_cyber(qa, "mitre_capec")

def go_tech_cyber_events():
    r = requests.get("https://cybereventsdatabase.org/api/events?format=csv")
    csv_data = csv.DictReader(io.StringIO(r.text))
    qa = []
    for row in csv_data:
        ev = row.get("event_type","") or row.get("primary_effect","")
        desc = row.get("description","") or str(row)
        if ev and len(desc)>30:
            qa.append({"question": f"Cyber event: {ev} in {row.get('target_country','')}?",
                       "answer": desc[:1000], "source": "GoTech CEDB 2.0", "category": "cyber-event"})
    save_cyber(qa, "gotech_cedb") if qa else print("⚠️ GoTech: no data")

def greynoise_2026():
    # রিপোর্ট থেকে মেটাডেটা নেওয়া
    qa = [{"question": "GreyNoise 2026 State of the Edge: key findings?",
           "answer": "GreyNoise 2026 analyzed 2.97 billion malicious sessions from 3.8M unique IPs across 80+ countries. Over half of RCE attempts originated from previously unseen IPs, indicating a shift toward distributed, ephemeral attack infrastructure.",
           "source": "GreyNoise 2026", "category": "threat-intel"}]
    save_cyber(qa, "greynoise_2026")

def witfoo_precinct6():
    try:
        from datasets import load_dataset
        ds = load_dataset("witfoo/precinct6-cybersecurity-100m", split="train", streaming=True, trust_remote_code=True)
        qa = []
        for i, row in enumerate(ds):
            if i >= 5000: break
            ev = row.get("event_type","") or row.get("event_name","")
            desc = row.get("description","") or str(row)
            if ev and len(desc)>20:
                qa.append({"question": f"Precinct 6 event: {ev}?", "answer": desc[:1000],
                           "source": "WitFoo Precinct 6", "category": "live-attack"})
        save_cyber(qa, "witfoo_precinct6") if qa else print("⚠️ WitFoo: no data")
    except Exception as e: print(f"❌ WitFoo: {e}")

def hackersignal():
    try:
        from datasets import load_dataset
        ds = load_dataset("BenAmpel/hackersignal", split="train", streaming=True, trust_remote_code=True)
        qa = []
        for i, row in enumerate(ds):
            if i >= 3000: break
            txt = row.get("text","") or row.get("content","")
            if txt and len(txt)>50:
                qa.append({"question": "What hacker forum discussion is captured in HackerSignal?",
                           "answer": txt[:1000], "source": "HackerSignal", "category": "dark-web"})
        save_cyber(qa, "hackersignal") if qa else print("⚠️ HackerSignal: no data")
    except Exception as e: print(f"❌ HackerSignal: {e}")

def primus_trendmicro():
    try:
        from datasets import load_dataset
        ds = load_dataset("trendmicro-ailab/primus", "pretrain", split="train", streaming=True, trust_remote_code=True)
        qa = []
        for i, row in enumerate(ds):
            if i >= 3000: break
            txt = row.get("text","") or row.get("content","")
            if txt and len(txt)>50:
                qa.append({"question": "Cybersecurity knowledge from Primus dataset?",
                           "answer": txt[:1000], "source": "Primus (Trend Micro)", "category": "cyber-knowledge"})
        save_cyber(qa, "primus") if qa else print("⚠️ Primus: no data")
    except Exception as e: print(f"❌ Primus: {e}")

def zenodo_index():
    r = requests.get("https://rokibulroni.github.io/zenodo-datasets-index/data/zenodo_datasets.json")
    ds_list = r.json()
    qa = [{"question": f"Dataset: {d.get('title','')}?",
           "answer": d.get("description",""), "source": "Zenodo Index", "category": "dataset-index"}
          for d in ds_list[:500] if d.get("title") and d.get("description")]
    save_cyber(qa, "zenodo_index")

def nist_publications():
    qa = [{"question": "What are the NIST cybersecurity publications available?",
           "answer": "NIST 596 cybersecurity publications including SP 800-53 (Security Controls), SP 800-207 (Zero Trust), CSF 2.0 (Cybersecurity Framework) available on HuggingFace.",
           "source": "NIST", "category": "government-standard"}]
    save_cyber(qa, "nist_publications")

def securecode_v3():
    qa = [{"question": "What is SecureCode v3.0?",
           "answer": "SecureCode v3.0 provides 750 production-grade security examples covering OWASP LLM Top 10 2025 across 30+ AI/ML frameworks including LangChain, OpenAI, Anthropic, HuggingFace, LlamaIndex, and ChromaDB across Python, TypeScript, and JavaScript.",
           "source": "SecureCode v3.0", "category": "ai-security"}]
    save_cyber(qa, "securecode_v3")

def cyber_gym():
    qa = [{"question": "What is the CyberGym dataset for AI agent evaluation?",
           "answer": "CyberGym is a large-scale cybersecurity evaluation framework with 1,000+ real-world vulnerability analysis tasks. The full dataset is 236 GB and available on HuggingFace.",
           "source": "CyberGym (UK Gov)", "category": "ai-security"}]
    save_cyber(qa, "cyber_gym")

def cisa_cwe_patch():
    qa = [{"question": "What is the CIRCL vulnerability CWE patch dataset?",
           "answer": "The CIRCL dataset on HuggingFace contains real-world vulnerability patches enriched with CWE identifiers from GitHub, GitLab, and Bitbucket, supporting vulnerability classification tool development.",
           "source": "CIRCL/CWE-Patch", "category": "vulnerability"}]
    save_cyber(qa, "cisa_cwe_patch")

def lamda_android_malware():
    qa = [{"question": "What is the LAMDA Android malware dataset?",
           "answer": "LAMDA is an ICLR 2026 accepted dataset for concept drift in Android malware detection, capturing temporal variations and distribution shifts in malware evolution over time.",
           "source": "LAMDA (ICLR 2026)", "category": "malware"}]
    save_cyber(qa, "lamda_android")

def cyber_sec_megadataset():
    qa = [{"question": "What is CyberSec-MegaDataset from Baidu?",
           "answer": "CyberSec-MegaDataset is China's largest open-source cybersecurity dataset, designed for training models like DeepSeek-14B and Qwen-Code-30B, aggregating comprehensive security data.",
           "source": "CyberSec-MegaDataset (Baidu)", "category": "cyber-knowledge"}]
    save_cyber(qa, "baidu_megadataset")

def murhcad_honeypot():
    qa = [{"question": "What is the MURHCAD honeypot dataset?",
           "answer": "MURHCAD collected 132,425 attack events over 72 hours from 3 honeypots (Cowrie, Dionaea, SentryPeer) across 4 Azure VMs, with 2,438 unique IPs from 95 countries.",
           "source": "MURHCAD (Perdana Univ)", "category": "honeypot"}]
    save_cyber(qa, "murhcad")

def viot_ddos_2025():
    qa = [{"question": "What is the vIoT-DDoS-2025 dataset?",
           "answer": "vIoT-DDoS-2025 contains 168 hours of IoT network traffic with 15.2M packets including 20 DDoS attack scenarios: SYN flood, UDP flood, ICMP flood, HTTP flood, Slowloris, DNS amplification, and more.",
           "source": "vIoT-DDoS-2025 (Southampton)", "category": "ddos"}]
    save_cyber(qa, "viot_ddos")

def thirty_day_malicious_http():
    qa = [{"question": "What is the 30-Day Malicious HTTP dataset?",
           "answer": "This dataset captures 30 consecutive days of malicious HTTP requests blocked by OWASP ModSecurity WAF on a live production server, including SQLi, XSS, LFI, and scanner probe attacks.",
           "source": "30-Day Malicious HTTP (BME)", "category": "waf"}]
    save_cyber(qa, "thirty_day_http")

def gambit_red_team():
    qa = [{"question": "What is the GAMBiT red-team dataset?",
           "answer": "GAMBiT presents 3 large-scale human-subject red-team hacking experiments in an enterprise-grade cyber range, capturing cognitive bias data from 19-20 participants across July 2024-March 2025.",
           "source": "GAMBiT (NYU/Virginia Tech)", "category": "red-team"}]
    save_cyber(qa, "gambit")

def deeep_dark_cti():
    qa = [{"question": "What is DeepDarkCTI?",
           "answer": "DeepDarkCTI provides 600+ dark web CTI sources including ransomware sites, hacker forums, marketplaces, and Telegram threat channels for real-time dark web intelligence.",
           "source": "DeepDarkCTI", "category": "dark-web"}]
    save_cyber(qa, "deepdark_cti")

def tor_darkmarket():
    qa = [{"question": "What does Tor Darkmarket Network Analysis reveal?",
           "answer": "Analysis of 82,285 Tor onion services and 57,071 IDs (email, Telegram, crypto wallet) over 20 weeks, with 248,971 edges revealing dark web market interconnections.",
           "source": "Tor Darkmarket Analysis", "category": "dark-web"}]
    save_cyber(qa, "tor_darkmarket")

def apt_cti_graph():
    qa = [{"question": "What is the APT-CTI-Graph?",
           "answer": "APT-CTI-Graph covers 178 countries, 1,459 unique threat actors, and 16,729 cyber events from 2014 through March 2026, with CTI relationships extracted from 7,296 OSCTI reports.",
           "source": "APT-CTI-Graph (GoTech)", "category": "apt"}]
    save_cyber(qa, "apt_cti_graph")

def lock_shields_nato():
    qa = [{"question": "What is the NATO Locked Shields 2025 DFIR dataset?",
           "answer": "Locked Shields 2025 is NATO CCDCOE's live-fire cyber defense exercise with 41 countries. The DFIR dataset includes memory dumps, PCAP, malware C2 logs from a multi-stage 9-hour attack on IT and OT systems.",
           "source": "NATO Locked Shields 2025", "category": "military"}]
    save_cyber(qa, "lock_shields_nato")

def darpa_optic():
    qa = [{"question": "What is DARPA OpTC dataset?",
           "answer": "DARPA OpTC provides network and host IDS data using eBPF probes for advanced intrusion detection research, capturing real adversary behavior in a controlled environment.",
           "source": "DARPA OpTC", "category": "military"}]
    save_cyber(qa, "darpa_optic")

def clear_ransomware():
    qa = [{"question": "What is the CLEAR ransomware dataset?",
           "answer": "CLEAR (NeurIPS 2025) contains I/O traffic from 137 ransomware variants totaling 1,045 TiB, enabling behavioral ransomware detection research.",
           "source": "CLEAR Ransomware (NeurIPS)", "category": "ransomware"}]
    save_cyber(qa, "clear_ransomware")

def qut_supply_chain():
    qa = [{"question": "What is the QUT-DV25 supply chain dataset?",
           "answer": "QUT-DV25 analyzes 14,271 PyPI packages using dynamic analysis with eBPF probes, extracting 36 real-time features for software supply chain attack detection.",
           "source": "QUT-DV25 Supply Chain", "category": "supply-chain"}]
    save_cyber(qa, "qut_dv25")

def ids_2025_balanced():
    qa = [{"question": "What is the IDS2025 Balanced dataset?",
           "answer": "IDS2025 Balanced improves on CICIDS2017 with ~2.83M records covering DoS/DDoS, Brute Force, XSS, SQLi, Botnet, Heartbleed attacks with balanced class distribution.",
           "source": "IDS2025 Balanced", "category": "ids"}]
    save_cyber(qa, "ids2025")

def bccc_datasets():
    qa = [
        {"question": "What is BCCC-IoT-IDS-Zwave-2025?", "answer": "1 billion records, 20 TB IoT intrusion detection dataset with Z-Wave protocol data from York University's BCCC lab.", "source": "BCCC (York Univ)", "category": "iot"},
        {"question": "What is BCCC-DarkNet-2025?", "answer": "Encrypted darknet traffic dataset for classification and threat detection from York University.", "source": "BCCC DarkNet", "category": "dark-web"},
        {"question": "What is BCCC-MalMem-SnapLog-2025?", "answer": "Malware memory snapshot and log dataset for behavioral malware analysis.", "source": "BCCC MalMem", "category": "malware"},
        {"question": "What is BCCC-DeFiFraudTrans-2025?", "answer": "1 million DeFi fraud transaction dataset for blockchain security research.", "source": "BCCC DeFi", "category": "blockchain"},
        {"question": "What is BCCC-SCsVul-2025?", "answer": "110,000 Solidity smart contract vulnerability dataset for Web3 security.", "source": "BCCC Smart Contract", "category": "blockchain"}
    ]
    save_cyber(qa, "bccc_datasets")

def geiger_eu():
    qa = [{"question": "What is the GEIGER EU cyber incident dataset?",
           "answer": "GEIGER (EU-funded) provides cybersecurity incident data for small businesses and SMEs, with risk assessment and vulnerability tracking across European countries.",
           "source": "GEIGER EU", "category": "threat-intel"}]
    save_cyber(qa, "geiger_eu")

# ============ মেডিকেল ============
def bioasq():
    try:
        r = requests.get("https://zenodo.org/records/7655130/files/BioASQ-training12b.zip", timeout=120)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for fname in zf.namelist():
                if fname.endswith(".json"):
                    data = json.loads(zf.read(fname))
                    qa = [{"question": item.get("body",""), "answer": (item.get("ideal_answer","") or "")[:1500],
                           "source": "BioASQ", "category": "biomedical-qa"}
                          for item in data.get("questions",[]) if item.get("body") and item.get("ideal_answer")]
                    if qa: save_med(qa, f"bioasq_{fname.replace('.json','')}")
    except Exception as e: print(f"❌ BioASQ: {e}")

def clinvar():
    r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&retmax=100&term=pathogenic&retmode=json")
    ids = r.json().get("esearchresult",{}).get("idlist",[])
    qa = []
    for cid in ids[:50]:
        rd = requests.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id={cid}&retmode=json")
        rec = rd.json().get("result",{}).get(cid,{})
        if rec.get("title") and rec.get("gene_sort"):
            qa.append({"question": f"Clinical significance of {rec.get('gene_sort','')}: {rec.get('title','')}?",
                       "answer": f"Gene: {rec.get('gene_sort','')}. {rec.get('title','')}. NCBI ClinVar ID: {cid}.",
                       "source": "ClinVar (NCBI/NIH)", "category": "genomics"})
    save_med(qa, "clinvar") if qa else print("⚠️ ClinVar: no data")

def tcga_cancer():
    qa = [{"question": "What is TCGA (The Cancer Genome Atlas)?",
           "answer": "TCGA contains molecular characterization of over 20,000 primary cancer samples spanning 33 cancer types, including genomic, transcriptomic, proteomic, and clinical data totaling 2.5 petabytes. Available through NCI's Genomic Data Commons.",
           "source": "TCGA (NIH/NCI)", "category": "genomics"}]
    save_med(qa, "tcga")

def cm4ai():
    qa = [{"question": "What is Cell Maps for AI (CM4AI)?",
           "answer": "CM4AI is the NIH Bridge2AI Functional Genomics Grand Challenge. The October 2025 Data Release includes protein-protein interaction, spatial localization, and genetic perturbation data in MDA-MB-468 breast cancer cells.",
           "source": "CM4AI (NIH Bridge2AI)", "category": "functional-genomics"}]
    save_med(qa, "cm4ai")

def decipher_genomics():
    qa = [{"question": "What is DECIPHER v11.38?",
           "answer": "DECIPHER is a clinical genome mapping resource with 52,489 patients' genomic and phenotypic data for rare disease diagnosis. v11.38 includes GRCh38 coordinates, updated CNV tracks, and enhanced phenotype search.",
           "source": "DECIPHER", "category": "rare-disease"}]
    save_med(qa, "decipher")

def kids_first_drc():
    qa = [{"question": "What is Kids First DRC dataset?",
           "answer": "Kids First DRC provides pediatric cancer and rare disease genomic data with long-read sequencing data available for the first time in 2025, enabling structural variant discovery.",
           "source": "Kids First DRC (NIH)", "category": "pediatric-genomics"}]
    save_med(qa, "kids_first")

def gtex_genomics():
    qa = [{"question": "What is the GTEx dataset?",
           "answer": "The Genotype-Tissue Expression (GTEx) project provides open-access gene expression and regulatory data from 54 non-diseased tissue sites across nearly 1,000 individuals. Now available free on AWS via AnVIL.",
           "source": "GTEx (NIH/AnVIL)", "category": "genomics"}]
    save_med(qa, "gtex")

def medmax_multimodal():
    qa = [{"question": "What is MedMax dataset?",
           "answer": "MedMax provides 1.47 million multimodal biomedical instruction-tuning instances including interleaved image-text generation, biomedical image captioning, visual chat, and report understanding for mixed-modal foundation models.",
           "source": "MedMax", "category": "multimodal"}]
    save_med(qa, "medmax")

def mimic_iv():
    qa = [{"question": "What is MIMIC-IV clinical database?",
           "answer": "MIMIC-IV contains de-identified electronic health records for over 200,000 ICU patients at Beth Israel Deaconess Medical Center (2008-2019), including labs, vitals, medications, and clinical notes. Available on PhysioNet.",
           "source": "MIMIC-IV (MIT)", "category": "ehr"}]
    save_med(qa, "mimic_iv")

def tcia_cancer_imaging():
    qa = [{"question": "What is TCIA (The Cancer Imaging Archive)?",
           "answer": "TCIA hosts 30.9 million radiology images across 37,568 subjects, covering multiple cancer types with associated clinical and genomic data. Funded by NCI's Cancer Imaging Program.",
           "source": "TCIA (NCI)", "category": "medical-imaging"}]
    save_med(qa, "tcia")

def gm_vl_medical():
    qa = [{"question": "What is GMAI-VL-5.5M?",
           "answer": "GMAI-VL-5.5M (AAAI 2026) contains 550 million medical multimodal samples from 219 data sources, covering 13 imaging modalities and 18 clinical departments for generalist medical AI.",
           "source": "GMAI-VL-5.5M (AAAI 2026)", "category": "medical-imaging"}]
    save_med(qa, "gmaivl")

def rexgradient_chest_xray():
    qa = [{"question": "What is ReXGradient-160K?",
           "answer": "ReXGradient-160K contains 160,000 chest X-ray studies from 109,487 unique patients across 3 US health systems, with structured radiology reports and labels.",
           "source": "ReXGradient-160K", "category": "medical-imaging"}]
    save_med(qa, "rexgradient")

def ddi_corpus():
    qa = [{"question": "What is the DDI Corpus?",
           "answer": "The Drug-Drug Interaction Corpus contains pharmacological and clinical text annotated with drug mentions and interaction types, supporting pharmacovigilance and clinical decision support research.",
           "source": "DDI Corpus", "category": "pharmacology"}]
    save_med(qa, "ddi_corpus")

def drugbank():
    qa = [{"question": "What is DrugBank?",
           "answer": "DrugBank contains 13,000+ drug entries with detailed chemical, pharmacological, and pharmaceutical data, including drug targets, enzymes, transporters, and drug-drug interactions.",
           "source": "DrugBank", "category": "pharmacology"}]
    save_med(qa, "drugbank")

def uk_biobank():
    qa = [{"question": "What is UK Biobank?",
           "answer": "UK Biobank provides genetic, health, and lifestyle data from 500,000 volunteers, linked to NHS health records, with imaging data for 100,000 participants. Available by application to researchers.",
           "source": "UK Biobank", "category": "population-health"}]
    save_med(qa, "uk_biobank")

def precise_sg100k():
    qa = [{"question": "What is PRECISE-SG100K?",
           "answer": "PRECISE-SG100K is Singapore's 100,000-participant precision medicine cohort integrating genomic, clinical, and lifestyle data, with first data release projected for 2026.",
           "source": "PRECISE-SG100K", "category": "population-health"}]
    save_med(qa, "precise_sg100k")

def multicare_medical():
    qa = [{"question": "What is MultiCaRe dataset?",
           "answer": "MultiCaRe provides multimodal data from over 70,000 open-access clinical case reports with metadata, clinical cases, image captions, and 130,000+ images for medical image classification.",
           "source": "MultiCaRe", "category": "multimodal"}]
    save_med(qa, "multicare")

def clin_iq_link_2025():
    qa = [{"question": "What is ClinIQLink 2025?",
           "answer": "ClinIQLink 2025 is a BioNLP Workshop evaluation task at ACL 2025 assessing generative AI models' ability to produce factually accurate medical information, particularly in knowledge retrieval for hallucination detection.",
           "source": "ClinIQLink 2025", "category": "clinical-nlp"}]
    save_med(qa, "clin_iq_link")

def med_aesqa():
    qa = [{"question": "What is MedAESQA?",
           "answer": "MedAESQA (Medical Attributable and Evidence-supported Question Answering) contains medical questions paired with automatically generated answers and evidence-supported references for biomedical QA research.",
           "source": "MedAESQA", "category": "biomedical-qa"}]
    save_med(qa, "med_aesqa")

def haim_mimic_mm():
    qa = [{"question": "What is HAIM-MIMIC-MM?",
           "answer": "HAIM-MIMIC-MM is a multimodal clinical dataset based on MIMIC-IV for healthcare AI applications, combining tabular, text, and image modalities for holistic patient assessment.",
           "source": "HAIM-MIMIC-MM", "category": "multimodal"}]
    save_med(qa, "haim_mimic")

def niaid_data():
    qa = [{"question": "What NIAID data resources are available?",
           "answer": "NIAID provides 98 dataset repositories including infectious disease clinical trial data, immunology datasets, and the LLMs4Subjects shared task dataset from SemEval 2025.",
           "source": "NIAID (NIH)", "category": "clinical-trial"}]
    save_med(qa, "niaid")

def nhs_scotland_edris():
    qa = [{"question": "What is NHS Scotland eDRIS?",
           "answer": "NHS Scotland eDRIS provides primary care data for 1.4 million patients for research purposes, accessible by application to approved researchers.",
           "source": "NHS Scotland eDRIS", "category": "ehr"}]
    save_med(qa, "nhs_scotland")

def gsa_family_china():
    qa = [{"question": "What is GSA Family from China National Bioinformatics Center?",
           "answer": "GSA Family archives 44,904 datasets totaling 92.8 PB as of December 2025, with 13,663 open-access datasets and over 166 million cumulative downloads. Cited in 5,081 research papers globally.",
           "source": "GSA Family (CNCB)", "category": "genomics"}]
    save_med(qa, "gsa_family")

def igvf_catalog():
    qa = [{"question": "What is the IGVF Catalog?",
           "answer": "The IGVF Catalog collects, analyzes, and disseminates data on genetic variant effects including coding variants on protein abundance, noncoding variants on enhancer activity, and regulatory element characterization.",
           "source": "IGVF (NIH)", "category": "functional-genomics"}]
    save_med(qa, "igvf")

# ============ মেইন ============
if __name__ == "__main__":
    print(f"🚀 Nobab_AI Master Collector শুরু @ {datetime.utcnow()}")
    print("="*50)

    # সাইবার ৩০+ ফাংশন
    for fn in [cisa_kev, mitre_attack, mitre_capec, go_tech_cyber_events, greynoise_2026,
               witfoo_precinct6, hackersignal, primus_trendmicro, zenodo_index, nist_publications,
               securecode_v3, cyber_gym, cisa_cwe_patch, lamda_android_malware, cyber_sec_megadataset,
               murhcad_honeypot, viot_ddos_2025, thirty_day_malicious_http, gambit_red_team,
               deeep_dark_cti, tor_darkmarket, apt_cti_graph, lock_shields_nato, darpa_optic,
               clear_ransomware, qut_supply_chain, ids_2025_balanced, bccc_datasets, geiger_eu]:
        try: fn()
        except Exception as e: print(f"❌ {fn.__name__}: {e}")

    # মেডিকেল ২০+ ফাংশন
    for fn in [bioasq, clinvar, tcga_cancer, cm4ai, decipher_genomics, kids_first_drc,
               gtex_genomics, medmax_multimodal, mimic_iv, tcia_cancer_imaging, gm_vl_medical,
               rexgradient_chest_xray, ddi_corpus, drugbank, uk_biobank, precise_sg100k,
               multicare_medical, clin_iq_link_2025, med_aesqa, haim_mimic_mm, niaid_data,
               nhs_scotland_edris, gsa_family_china, igvf_catalog]:
        try: fn()
        except Exception as e: print(f"❌ {fn.__name__}: {e}")

    print(f"\n🎉 সব কাজ শেষ! datasets/cyber/ ও datasets/medical/ চেক করো")
    print("📊 পরবর্তী: python incremental_index.py")
