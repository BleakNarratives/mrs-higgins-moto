# Author: BleakNarratives
# Filename: bookkeeper.py
# Path: G:\Foxwood\moto-2024-sd-r26\bookkeeper.py

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

LOG_PATH     = "front_desk_routing_log.json"
SUMMARY_PATH = "income_summary.json"

def check_payment(lnbits_url, invoice_key, payment_hash):
    """
    GET /api/v1/payments/{payment_hash}
    Returns True if settled, False otherwise.
    """
    if not lnbits_url or not invoice_key or not payment_hash:
        return None  # can't check
    req = urllib.request.Request(
        f"{lnbits_url.rstrip('/')}/api/v1/payments/{payment_hash}",
        headers={"X-Api-Key": invoice_key},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("paid", False)
    except Exception as e:
        print(f"  [LNbits] Check failed for {payment_hash[:12]}: {e}")
        return None

def run():
    lnbits_url   = os.getenv("LNBITS_URL", "")
    invoice_key  = os.getenv("LNBITS_INVOICE_KEY", "")

    if not os.path.exists(LOG_PATH):
        print(f"[ABORT] {LOG_PATH} not found. Run front_desk_lady.py first.")
        return

    with open(LOG_PATH, "r") as f:
        log = json.load(f)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_routed": len(log),
        "settled": [],
        "pending": [],
        "untracked": []
    }

    for entry in log:
        name   = entry.get("package_name", "unknown")
        platform = entry.get("platform", "unknown")
        # front_desk_lady writes payment_id (Voltage), older flows wrote payment_hash
        phash  = entry.get("payment_hash") or entry.get("payment_id")
        status = entry.get("status")

        if status == "DRY_RUN":
            summary["untracked"].append({"package": name, "platform": platform, "reason": status or "no_hash"})
            print(f"  [SKIP] {name} / {platform} — no hash")
            continue

        record = {"package": name, "platform": platform, "payment_hash": phash}

        # Live-routed but no payment handle available: still track as pending follow-up
        if not phash:
            summary["pending"].append({**record, "reason": "no_payment_id"})
            print(f"  [PEND] {name} / {platform} (no payment id)")
            continue

        # If no checker config is set, keep as pending so the closer can follow up.
        if not lnbits_url or not invoice_key:
            summary["pending"].append({**record, "reason": "checker_not_configured"})
            print(f"  [PEND] {name} / {platform} (checker not configured)")
            continue

        paid = check_payment(lnbits_url, invoice_key, phash)

        if paid is True:
            summary["settled"].append(record)
            print(f"  [PAID] {name} / {platform}")
        elif paid is False:
            summary["pending"].append(record)
            print(f"  [PEND] {name} / {platform}")
        else:
            summary["untracked"].append({**record, "reason": "check_failed"})
            print(f"  [ERR]  {name} / {platform}")

    summary["settled_count"] = len(summary["settled"])
    summary["pending_count"] = len(summary["pending"])
    summary["untracked_count"] = len(summary["untracked"])

    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[DONE] settled={summary['settled_count']} pending={summary['pending_count']} untracked={summary['untracked_count']}")
    print(f"       → {SUMMARY_PATH}")

if __name__ == "__main__":
    run()
