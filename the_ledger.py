#!/usr/bin/env python3
# Author: BleakNarratives
# Filename: the_ledger.py
# Path: G:\Foxwood\moto-2024-sd-r26\the_ledger.py
#
# The Ledger — correlation engine for the Vertical AI pipeline.
# Reads all output files, cross-references everything, tells you
# what's actually working and what to stop wasting time on.
# No cloud. No deps outside stdlib.

import json
import os
from datetime import datetime, timezone
from collections import defaultdict

# ── Input files ──────────────────────────────────────────────
ROUTING_LOG   = "front_desk_routing_log.json"
INCOME_SUMMARY = "income_summary.json"
LEADS_FILE    = "scout_leads.json"
COPY_DIR      = "./copy_output"
PACKAGES_DIR  = "./saas_packages"

# ── Output ───────────────────────────────────────────────────
LEDGER_PATH   = "the_ledger.json"
REPORT_PATH   = "the_ledger_report.txt"

BAR  = "─" * 50
DBAR = "═" * 50

def load(path, fallback=None):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load {path}: {e}")
    return fallback if fallback is not None else []

def load_packages():
    pkgs = {}
    if not os.path.exists(PACKAGES_DIR):
        return pkgs
    for fname in os.listdir(PACKAGES_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(PACKAGES_DIR, fname)) as f:
                    p = json.load(f)
                    pkgs[p.get("name", fname)] = p
            except Exception:
                pass
    return pkgs

def count_copy_files():
    """Returns {package_platform_slug: True} for generated copy."""
    if not os.path.exists(COPY_DIR):
        return {}
    return {f.replace(".md", ""): True for f in os.listdir(COPY_DIR) if f.endswith(".md")}

def score_package(name, platform, settled_set, pending_set, leads, copy_files):
    """
    Returns a numeric score and label for a package+platform combo.
    Higher = more pipeline activity = more signal = keep going.
    """
    score = 0
    reasons = []
    slug = f"{name.lower().replace(' ', '_')}_{platform.lower()}"

    if (name, platform) in settled_set:
        score += 10
        reasons.append("payment settled (+10)")

    if (name, platform) in pending_set:
        score += 4
        reasons.append("payment pending (+4)")

    lead_hits = sum(1 for l in leads if l.get("package") == name)
    if lead_hits:
        score += lead_hits * 3
        reasons.append(f"{lead_hits} scout lead(s) (+{lead_hits*3})")

    if slug in copy_files:
        score += 2
        reasons.append("copy generated (+2)")

    return score, reasons

def label(score):
    if score >= 10: return "🟢 SHIPPING"
    if score >= 6:  return "🟡 WARM"
    if score >= 2:  return "🔵 IN PLAY"
    return            "⚪ COLD"

def build_ledger():
    routing   = load(ROUTING_LOG)
    summary   = load(INCOME_SUMMARY, fallback={})
    leads     = load(LEADS_FILE)
    packages  = load_packages()
    copy_files = count_copy_files()

    settled_set = {(e["package"], e["platform"]) for e in summary.get("settled", [])}
    pending_set = {(e["package"], e["platform"]) for e in summary.get("pending", [])}

    # Build unique package+platform combos from routing log
    combos = {}
    for entry in routing:
        name     = entry.get("package_name", "unknown")
        platform = entry.get("platform", "unknown")
        key = (name, platform)
        if key not in combos:
            combos[key] = {"routes": 0, "dry_runs": 0}
        if entry.get("status") == "DRY_RUN":
            combos[key]["dry_runs"] += 1
        else:
            combos[key]["routes"] += 1

    # Also pull from packages dir for anything not yet routed
    for pname in packages:
        pkg = packages[pname]
        for platform in pkg.get("target_platforms", ["Fiverr", "Upwork"]):
            key = (pname, platform)
            if key not in combos:
                combos[key] = {"routes": 0, "dry_runs": 0}

    ledger = []
    for (name, platform), counts in sorted(combos.items()):
        score, reasons = score_package(
            name, platform, settled_set, pending_set, leads, copy_files
        )
        ledger.append({
            "package":    name,
            "platform":   platform,
            "score":      score,
            "label":      label(score),
            "routes":     counts["routes"],
            "dry_runs":   counts["dry_runs"],
            "reasons":    reasons,
        })

    ledger.sort(key=lambda x: x["score"], reverse=True)
    return ledger, leads, settled_set, pending_set, packages

def platform_breakdown(ledger):
    by_platform = defaultdict(list)
    for entry in ledger:
        by_platform[entry["platform"]].append(entry["score"])
    return {
        p: {
            "count":   len(scores),
            "avg":     round(sum(scores) / len(scores), 1),
            "total":   sum(scores),
        }
        for p, scores in by_platform.items()
    }

def write_report(ledger, leads, settled_set, pending_set, packages):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    lines += [
        DBAR,
        f"  THE LEDGER — Vertical AI Pipeline Signal Report",
        f"  Generated: {now}",
        DBAR,
        "",
    ]

    # ── Summary ──
    shipping = [e for e in ledger if e["score"] >= 10]
    warm     = [e for e in ledger if 6 <= e["score"] < 10]
    cold     = [e for e in ledger if e["score"] < 2]

    lines += [
        "OVERVIEW",
        BAR,
        f"  Packages tracked : {len(set(e['package'] for e in ledger))}",
        f"  Platform combos  : {len(ledger)}",
        f"  Settled payments : {len(settled_set)}",
        f"  Pending payments : {len(pending_set)}",
        f"  Scout leads      : {len(leads)}",
        "",
        f"  🟢 SHIPPING  : {len(shipping)}",
        f"  🟡 WARM      : {len(warm)}",
        f"  ⚪ COLD       : {len(cold)}",
        "",
    ]

    # ── Per-package scores ──
    lines += ["PACKAGE SCORES", BAR]
    for e in ledger:
        lines.append(
            f"  {e['label']:<14} {e['package']:<28} [{e['platform']}]  score={e['score']}"
        )
        for r in e["reasons"]:
            lines.append(f"    ↳ {r}")
        if not e["reasons"]:
            lines.append(f"    ↳ no pipeline activity yet")
    lines.append("")

    # ── Platform breakdown ──
    breakdown = platform_breakdown(ledger)
    lines += ["PLATFORM BREAKDOWN", BAR]
    for p, stats in sorted(breakdown.items(), key=lambda x: -x[1]["avg"]):
        lines.append(f"  {p:<12}  avg_score={stats['avg']}  packages={stats['count']}")
    lines.append("")

    # ── Actionable calls ──
    lines += ["WHAT TO DO", BAR]
    calls = []

    if shipping:
        calls.append(f"► Double down: {', '.join(e['package'] for e in shipping[:3])}")
    if warm:
        calls.append(f"► Push to close: {', '.join(e['package'] for e in warm[:3])}")
    if cold:
        calls.append(f"► Consider cutting or reworking: {', '.join(e['package'] for e in cold[:3])}")
    if len(leads) == 0:
        calls.append("► No scout leads yet — fix Scout or expand search terms")
    if len(settled_set) == 0 and len(pending_set) == 0:
        calls.append("► No payment activity — confirm LNbits is live and invoices are reaching clients")

    if not calls:
        calls.append("► Pipeline looks healthy. Run it again tomorrow.")

    for c in calls:
        lines.append(f"  {c}")

    lines += ["", DBAR, ""]

    report = "\n".join(lines)
    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(report)
    return report

def run():
    ledger, leads, settled_set, pending_set, packages = build_ledger()

    with open(LEDGER_PATH, "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "entries": ledger
        }, f, indent=2)

    write_report(ledger, leads, settled_set, pending_set, packages)
    print(f"[SAVED] {LEDGER_PATH}")
    print(f"[SAVED] {REPORT_PATH}")

if __name__ == "__main__":
    run()
