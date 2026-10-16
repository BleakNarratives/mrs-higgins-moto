# Vertical AI — Passive Income Pipeline
### moto-2024-sd-r26
**Author:** BleakNarratives  
**Stack:** Python · Lightning Network · Voltage Payments · Ollama · Termux/aarch64  
**Path:** `/storage/ED7B-AD5A/root_2026/moto-2024-sd-r26/`

---

## What This Is

A fully local, autonomous SaaS routing pipeline that runs on an Android phone.
No cloud dependencies for the core loop. No VC. No team. Just the crew.

It loads product packages, generates platform-specific listings, creates Lightning
invoices, follows up on unpaid leads, reconciles payments, and tells you what's
actually working — all from a single shell command.

---

## The Crew

| Script | Role |
|---|---|
| `front_desk_lady.py` | Mrs. Higgins. Loads packages, routes to platforms, creates Voltage invoices. She ships. |
| `bookkeeper.py` | Reconciles payment hashes against Voltage API. Produces `income_summary.json`. |
| `the_closer.py` | Reads pending payments, fires Telegram follow-ups. Stateless, cron-friendly. |
| `copywriter.py` | Ollama-powered copy generator. Writes platform-specific listings to `copy_output/`. |
| `scout.py` | Watches Fiverr/Upwork for inbound leads matching your packages. |
| `the_ledger.py` | Correlation engine. Scores every package+platform combo. Tells you what to keep doing. |
| `briefing.py` | Morning terminal summary. Run this first. Tells you what needs your hands today. |
| `mrs_higgins.sh` | Master launcher. Runs the full crew in order with logging. |
| `setup.sh` | First-time scaffolding. Directories, config template, Ollama check. |

---

## Directory Structure

```
moto-2024-sd-r26/
├── saas_packages/          # One JSON file per product offering
├── copy_output/            # Generated platform copy (Fiverr/Upwork/Nostr)
├── logs/                   # Pipeline run logs (timestamped)
├── front_desk_config.json  # API keys and Lightning config
├── front_desk_routing_log.json  # Written by Mrs. Higgins
├── income_summary.json     # Written by Bookkeeper
├── scout_leads.json        # Written by Scout
├── closer_sent.json        # Dedup log for Telegram messages
├── the_ledger.json         # Scored package data
└── the_ledger_report.txt   # Human-readable signal report
```

---

## Package Format

Each file in `saas_packages/` is a JSON product definition:

```json
{
  "name": "Local AI Chatbot Setup",
  "tagline": "Your own private AI. No subscriptions.",
  "description": "Full description of what you deliver.",
  "features": ["Feature one", "Feature two"],
  "target_platforms": ["Fiverr", "Upwork", "Nostr"],
  "pricing_model": "Flat fee $149",
  "price_sats": 150000,
  "estimated_roi_per_business": "Replaces $20-100/month ChatGPT bill",
  "delivery_days": 3
}
```

---

## Config

`front_desk_config.json`:
```json
{
  "lightning_account_id": "bleaknarratives@speed.app",
  "lnbits_url": "https://payments.voltage.cloud",
  "voltage_api_key": "YOUR_KEY_HERE"
}
```

**Environment variables** (override config file):
- `VOLTAGE_API_KEY`
- `LIGHTNING_ACCOUNT_ID`
- `OLLAMA_URL` (default: `http://localhost:11434`)
- `OLLAMA_MODEL` (default: `qwen2.5:1.5b`)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `LNBITS_INVOICE_KEY` (legacy)

---

## Running It

```bash
# First time
bash setup.sh

# Every morning
python briefing.py

# Full pipeline
bash mrs_higgins.sh

# Dry run (no invoices, no Telegram)
bash mrs_higgins.sh --dry-run

# Single platform
bash mrs_higgins.sh --platform Fiverr

# Individual scripts
python front_desk_lady.py --dry-run
python bookkeeper.py
python the_closer.py
python copywriter.py --platform Nostr
python scout.py --watch
python the_ledger.py
```

---

## Intended Run Order

```
briefing.py         ← what needs attention
front_desk_lady.py  ← route packages, create invoices  
bookkeeper.py       ← reconcile payments
the_closer.py       ← follow up on pending
copywriter.py       ← generate listings
scout.py            ← find inbound leads
the_ledger.py       ← score what's working
```

---

## ZeroClaw / Crown Integration (WIP)

Crown (`crown-jules`) provides a Jules API bridge for autonomous code improvement.
Molt watchdog applies arena-winning diffs. Crown submits them to Jules for review
and commits back to the repo. ZeroClaw broadcasts results to Nostr.

```bash
# Once crown is built and auth'd:
echo "Apply winning diffs from arena run, test, commit" | \
  crown molt --repo BleakNarratives/zeroclaw --stdin
```

Crown binary: build from `/storage/ED7B-AD5A/root_2026/crown-jules/`
```bash
cd /storage/ED7B-AD5A/root_2026/crown-jules
RUSTFLAGS="-C linker=ld.lld" cargo build --release
cp target/release/crown ~/.local/bin/
crown auth YOUR_JULES_API_KEY
```

---

## Notes

- `sed -i` does not work directly on SD card paths — copy to `~/`, edit, copy back
- Ollama crashes under RAM pressure — `qwen2.5:1.5b` is the stable default
- Scout requires `selenium` + headless Chromium — heavy on Termux, run sparingly
- The Ledger scoring: settled=+10, pending=+4, lead hit=+3, copy exists=+2

---

## Lore

*Syntax AI is the soul. Crown is the hands. Mrs. Higgins runs the office.*  
*She doesn't accept excuses. She ships.*

---

*Bleak Narratives was here.*
