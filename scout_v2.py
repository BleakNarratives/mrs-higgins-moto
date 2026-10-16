#!/usr/bin/env python3
# Author: BleakNarratives
# Filename: scout.py
# Path: /storage/ED7B-AD5A/root_2026/moto-2024-sd-r26/scout.py
#
# Scout — inbound lead finder. No Selenium. No Chrome. Pure stdlib HTTP.

import json, os, re, time, argparse
import urllib.request, urllib.parse, urllib.error
from datetime import datetime

LEADS_PATH    = "scout_leads.json"
PACKAGES_DIR  = "./saas_packages"
POLL_INTERVAL = int(os.getenv("SCOUT_INTERVAL", "300"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Moto G) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

BOARDS = [
    ("Upwork", "https://www.upwork.com/search/jobs/?q={query}&sort=recency"),
    ("Fiverr", "https://www.fiverr.com/search/gigs?query={query}"),
]

def load_packages(d=PACKAGES_DIR):
    pkgs = []
    if not os.path.exists(d): return pkgs
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            try:
                with open(os.path.join(d, f)) as fh: pkgs.append(json.load(fh))
            except: pass
    return pkgs

def extract_keywords(pkg):
    words = set()
    for field in ("name", "tagline", "description"):
        words.update(re.findall(r'\b\w{4,}\b', pkg.get(field, "").lower()))
    noise = {"with","that","this","your","from","have","will","been","also","more",
             "just","each","into","their","they","what","when","which","local","without"}
    return list(words - noise)[:5]

def fetch_page(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        print(f"    [HTTP {e.code}]"); return None
    except Exception as e:
        print(f"    [ERR] {e}"); return None

def scrape_board(board, url_tmpl, keywords, pkg_name):
    query = urllib.parse.quote_plus(" ".join(keywords[:3]))
    url   = url_tmpl.format(query=query)
    print(f"  [{board}] {url[:65]}", end=" ", flush=True)
    html  = fetch_page(url)
    if not html: return []
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).lower()
    matched = [kw for kw in keywords if kw in text]
    if matched:
        print(f"→ HIT {matched}")
        return [{"package": pkg_name, "board": board, "url": url,
                 "matched_kw": matched, "found_at": datetime.utcnow().isoformat()+"Z"}]
    print("→ miss"); return []

def load_leads():
    if os.path.exists(LEADS_PATH):
        with open(LEADS_PATH) as f: return json.load(f)
    return []

def save_leads(leads):
    with open(LEADS_PATH, "w") as f: json.dump(leads, f, indent=2)

def dedup(existing, new):
    seen = {(l["package"], l["board"], l["url"]) for l in existing}
    return existing + [l for l in new if (l["package"], l["board"], l["url"]) not in seen]

def run_once(packages_dir=PACKAGES_DIR):
    packages = load_packages(packages_dir)
    if not packages: print("[ABORT] No packages."); return
    leads, new_leads = load_leads(), []
    for pkg in packages:
        name = pkg.get("name", "unnamed")
        kw   = extract_keywords(pkg)
        print(f"\n[SCOUT] '{name}' — {kw[:3]}")
        for board, tmpl in BOARDS:
            new_leads.extend(scrape_board(board, tmpl, kw, name))
            time.sleep(2)
    merged = dedup(leads, new_leads)
    save_leads(merged)
    print(f"\n[DONE] {len(new_leads)} new lead(s) → {LEADS_PATH} (total: {len(merged)})")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages-dir", default=PACKAGES_DIR)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    if args.watch:
        while True:
            run_once(args.packages_dir)
            time.sleep(POLL_INTERVAL)
    else:
        run_once(args.packages_dir)

if __name__ == "__main__":
    main()
