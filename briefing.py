#!/usr/bin/env python3
# Author: BleakNarratives
# Filename: briefing.py
# Path: G:\Foxwood\moto-2024-sd-r26\briefing.py
# Run this first thing. It tells you what actually needs your hands today.

import json
import os
from datetime import datetime, timezone

BAR = "─" * 44

def load(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def section(title):
    print(f"\n{BAR}")
    print(f"  {title}")
    print(BAR)

def age(iso):
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - t
        h = int(delta.total_seconds() // 3600)
        return f"{h}h ago" if h < 48 else f"{delta.days}d ago"
    except Exception:
        return "?"

def run():
    now = datetime.now().strftime("%A %b %d, %H:%M")
    print(f"\n{'='*44}")
    print(f"  MRS. HIGGINS DAILY BRIEFING — {now}")
    print(f"{'='*44}")

    # --- Income Summary ---
    summary = load("income_summary.json")
    section("💰 PAYMENTS")
    if summary:
        print(f"  Settled  : {summary.get('settled_count', 0)}")
        print(f"  Pending  : {summary.get('pending_count', 0)}")
        print(f"  Untracked: {summary.get('untracked_count', 0)}")
        print(f"  As of    : {age(summary.get('generated_at',''))}")
        if summary.get("pending"):
            print(f"\n  Needs chasing:")
            for e in summary["pending"][:3]:
                print(f"    → {e['package']} / {e['platform']}")
    else:
        print("  No income_summary.json — run bookkeeper.py")

    # --- Scout Leads ---
    leads = load("scout_leads.json")
    section("🔍 LEADS (Scout)")
    if leads:
        recent = sorted(leads, key=lambda x: x.get("found_at",""), reverse=True)[:5]
        print(f"  Total leads on file: {len(leads)}")
        print(f"  Most recent:")
        for l in recent:
            print(f"    [{l.get('board','?')}] {l.get('package','?')} — {age(l.get('found_at',''))}")
    else:
        print("  No leads yet — run scout.py")

    # --- Routing Log ---
    log = load("front_desk_routing_log.json")
    section("📦 ROUTING LOG")
    if log:
        dry   = sum(1 for e in log if e.get("status") == "DRY_RUN")
        live  = sum(1 for e in log if e.get("status") == "Routed")
        print(f"  Routed (live): {live}")
        print(f"  Dry runs     : {dry}")
    else:
        print("  No routing log — run front_desk_lady.py")

    # --- Copy Output ---
    section("✍️  COPY OUTPUT")
    copy_dir = "./copy_output"
    if os.path.exists(copy_dir):
        files = [f for f in os.listdir(copy_dir) if f.endswith(".md")]
        print(f"  {len(files)} copy file(s) in ./copy_output/")
        for f in sorted(files)[:5]:
            print(f"    {f}")
    else:
        print("  No copy yet — run copywriter.py")

    # --- Run Logs ---
    section("📋 LAST PIPELINE RUN")
    log_dir = "./logs"
    if os.path.exists(log_dir):
        runs = sorted(os.listdir(log_dir), reverse=True)
        if runs:
            last = runs[0]
            path = os.path.join(log_dir, last)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            print(f"  {last}")
            print(f"  Run at: {mtime.strftime('%b %d %H:%M')}")
        else:
            print("  No runs logged yet.")
    else:
        print("  No logs/ dir — run mrs_higgins.sh first")

    # --- Today's focus ---
    section("🎯 FOCUS")
    flags = []
    if summary and summary.get("pending_count", 0) > 0:
        flags.append("Chase pending payments → the_closer.py")
    if leads and len(leads) > 0:
        flags.append("Review new leads → scout_leads.json")
    if not os.path.exists(copy_dir) or not os.listdir(copy_dir):
        flags.append("Generate copy → copywriter.py")
    if not flags:
        flags.append("Run the pipeline → bash mrs_higgins.sh")
    for f in flags:
        print(f"  ► {f}")

    print(f"\n{'='*44}\n")

if __name__ == "__main__":
    run()
