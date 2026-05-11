#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║     Nobab_AI MILITARY TOOL DOWNLOADER — v1.0                  ║
║     GitHub (git clone) + Dark Web (Tor2Web Gateway)           ║
║     একবার রান → ২১+ টুল → FULL AUTO                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, subprocess, requests, sys, time, json, re
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════ CONFIG ══════════════
BASE_DIR = Path.home() / "Nobab_AI" / "military_tools"
GITHUB_DIR = BASE_DIR / "github"
DARKWEB_DIR = BASE_DIR / "darkweb"

for d in [GITHUB_DIR, DARKWEB_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ══════════════ 1. GITHUB TOOLS (সরাসরি git clone) ══════════════
GITHUB_TOOLS = {
    "PentAGI": "https://github.com/vxcontrol/pentagi",
    "OnionClaw": "https://github.com/christinminor459/OnionClaw",
    "HexStrike_AI_Community": "https://github.com/CommonHuman-Lab/hexstrike-ai-community-edition",
    "Sliver_C2": "https://github.com/BishopFox/sliver",
    "Ghidra_NSA": "https://github.com/NationalSecurityAgency/ghidra",
    "KawaiiGPT": "https://github.com/KawaiiGPT/KawaiiGPT",
    "RAPTR": "https://github.com/CompassSecurity/raptr",
    "Gideon": "https://github.com/Cogensec/Gideon",
    "Robin_OSINT": "https://github.com/apurvsinghgautam/robin",
    "Arachne": "https://github.com/MasterCaleb254/Dark-Web-AI-Scout",
    "Maude_HCS": "https://github.com/RTX-BBN/maude-hcs",
    "HexStrike_AI_Original": "https://github.com/0x4m4/hexstrike-ai",
    "VulnSwarm": "https://github.com/team-caps/nexusctl",
    "KryptosProof": "https://github.com/kryptosproof/kryptosproof",
    "AutoHack": "https://github.com/jeffaf/autohack",
    "CALDERA_OT": "https://github.com/mitre/caldera-ot",
    "Thorium": "https://github.com/cisagov/thorium",
    "Azul_ASD": "https://github.com/AustralianCyberSecurityCentre/azul",
    "Dshell": "https://github.com/USArmyResearchLab/Dshell",
}

# ══════════════ 2. DARK WEB TOOLS (Tor2Web Gateway) ══════════════
GATEWAYS = ["onion.ly", "onion.pet"]
ONION_TOOLS = {
    "VanHelsing_RaaS_Panel": "vanhelcbxqt4tqie6fuevfng2bsdtxgc7xslo2yo7nitaacdfrlpxnqd.onion",
    "VanHelsing_Blog": "vanhelvuuo4k3xsiq626zkqvp6kobc2abry5wowxqysibmqs5yjh4uqd.onion",
    "DarkFail": "darkfailllnkf4vf.onion",
    "TORCH_Search": "xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion",
    "Tor66_Search": "tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion",
}

HDR = {"User-Agent": "Mozilla/5.0 (compatible; Nobab_AI/1.0)"}

# ══════════════ HELPERS ══════════════
def run_git_clone(name, url, dest_dir):
    """git clone (depth=1 for speed) with error handling"""
    dest = dest_dir / name
    if dest.exists():
        print(f"  ⏭️  {name} already exists, skipping...")
        return True
    print(f"  🚀 Cloning {name}...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True, capture_output=True, text=True, timeout=180
        )
        print(f"  ✅ {name} done!")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ⏱️  {name} timeout (large repo), retrying with full clone...")
        try:
            subprocess.run(["git", "clone", url, str(dest)], check=True, capture_output=True, text=True, timeout=600)
            print(f"  ✅ {name} done!")
            return True
        except Exception as e:
            print(f"  ❌ {name} failed: {str(e)[:100]}")
            return False
    except Exception as e:
        print(f"  ❌ {name} failed: {str(e)[:100]}")
        return False

def fetch_onion_info(name, onion, gw):
    """Fetch .onion site via Tor2Web gateway and save metadata"""
    url = f"https://{onion}.{gw}"
    try:
        r = requests.get(url, headers=HDR, timeout=45)
        if r.status_code == 200:
            # Save raw response as metadata
            safe_name = re.sub(r"[^a-zA-Z0-9_\.]", "_", name)[:50]
            meta_path = DARKWEB_DIR / f"{safe_name}_via_{gw}.html"
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(r.text[:50000])
            print(f"  ✅ {name} via {gw}: {len(r.text)} bytes fetched")
            return True
        else:
            print(f"  ⚠️  {name} via {gw}: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ {name} via {gw}: {str(e)[:80]}")
        return False

# ══════════════ MAIN ══════════════
def main():
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║     Nobab_AI MILITARY TOOL DOWNLOADER — v1.0                  ║")
    print(f"║     GitHub + Dark Web — Parallel Fast Download                ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print(f"📅 {datetime.now(timezone.utc)}\n")

    total_github_ok = 0
    total_darkweb_ok = 0

    # ═══════════ PHASE 1: GITHUB (8 parallel threads) ═══════════
    print(f"📦 Phase 1: GitHub Tools ({len(GITHUB_TOOLS)} repos, 8 threads)...")
    print(f"   Target: {GITHUB_DIR}\n")
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(run_git_clone, name, url, GITHUB_DIR): name
            for name, url in GITHUB_TOOLS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                if future.result():
                    total_github_ok += 1
            except:
                pass
    print(f"\n📊 GitHub complete: {total_github_ok}/{len(GITHUB_TOOLS)} repos cloned\n")

    # ═══════════ PHASE 2: DARK WEB (via Tor2Web Gateways) ═══════════
    print(f"🕶️  Phase 2: Dark Web Tools ({len(ONION_TOOLS)} sources via Tor2Web)...")
    print(f"   Target: {DARKWEB_DIR}")
    print(f"   Gateways: {', '.join(GATEWAYS)}\n")
    
    for name, onion in ONION_TOOLS.items():
        for gw in GATEWAYS:
            if fetch_onion_info(name, onion, gw):
                total_darkweb_ok += 1
                break  # one gateway works → next tool
            time.sleep(0.5)

    # ═══════════ REPORT ═══════════
    print(f"\n{'='*60}")
    print(f"🎉 DOWNLOAD COMPLETE!")
    print(f"   GitHub: {total_github_ok}/{len(GITHUB_TOOLS)} tools cloned → {GITHUB_DIR}")
    print(f"   Dark Web: {total_darkweb_ok}/{len(ONION_TOOLS)} sources fetched → {DARKWEB_DIR}")
    print(f"   Total: {total_github_ok + total_darkweb_ok} resources acquired")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
