# Author: BleakNarratives
# Filename: the_closer.py
# Path: G:\Foxwood\moto-2024-sd-r26\the_closer.py

import json
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

LOG_PATH     = "front_desk_routing_log.json"
SUMMARY_PATH = "income_summary.json"
SENT_LOG     = "closer_sent.json"

def telegram_send(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("ok", False)
    except Exception as e:
        print(f"  [Telegram] Send failed: {e}")
        return False

def load_sent_log():
    if os.path.exists(SENT_LOG):
        with open(SENT_LOG, "r") as f:
            return json.load(f)
    return {}

def save_sent_log(sent):
    with open(SENT_LOG, "w") as f:
        json.dump(sent, f, indent=2)

def build_message(entry, source="routing_log"):
    name     = entry.get("package", entry.get("package_name", "unknown"))
    platform = entry.get("platform", "unknown")
    phash    = entry.get("payment_hash", "N/A")
    reason   = entry.get("reason", "pending")
    return (
        f"📬 *The Closer — Follow-Up Required*\n"
        f"Package: `{name}`\n"
        f"Platform: `{platform}`\n"
        f"Status: `{reason}`\n"
        f"Hash: `{phash[:16] if phash and phash != 'N/A' else 'none'}`\n"
        f"Time: `{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC`"
    )

def run():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id   = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print("[ABORT] Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.")
        return

    # Prefer income_summary.json (post-bookkeeper) — fall back to raw routing log
    pending = []
    if os.path.exists(SUMMARY_PATH):
        with open(SUMMARY_PATH, "r") as f:
            summary = json.load(f)
        pending = summary.get("pending", []) + summary.get("untracked", [])
        print(f"[SOURCE] {SUMMARY_PATH} — {len(pending)} actionable entries")
    elif os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            raw = json.load(f)
        pending = [e for e in raw if e.get("status") not in ("DRY_RUN",)]
        print(f"[SOURCE] {LOG_PATH} (raw) — {len(pending)} entries")
    else:
        print(f"[ABORT] Neither {SUMMARY_PATH} nor {LOG_PATH} found.")
        return

    sent = load_sent_log()
    fired = 0

    for entry in pending:
        key = f"{entry.get('package', entry.get('package_name'))}:{entry.get('platform')}:{entry.get('payment_hash','')}"
        if key in sent:
            print(f"  [SKIP] Already sent: {key[:40]}")
            continue
        msg = build_message(entry)
        ok = telegram_send(bot_token, chat_id, msg)
        if ok:
            sent[key] = datetime.utcnow().isoformat() + "Z"
            fired += 1
            print(f"  [SENT] {entry.get('package', '?')} / {entry.get('platform', '?')}")
        else:
            print(f"  [FAIL] {entry.get('package', '?')} / {entry.get('platform', '?')}")

    save_sent_log(sent)
    print(f"\n[DONE] {fired} message(s) fired → {SENT_LOG}")

if __name__ == "__main__":
    run()
