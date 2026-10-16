# Mrs. Higgins

> *"The eyes and ears on the ground."*

WiFi-triggered real-world interface agent. Part of the **Vertical AI / ZeroClaw** ecosystem by BleakNarratives.

Whenever a device with Mrs. Higgins installed connects to WiFi, she wakes up, pings the local Ollama instance, and reports status. She is the real-world sensory layer — the part of the boardroom that touches actual infrastructure.

---

## What She Does

- Polls WiFi state every 10 seconds
- On **connect** → fires Ollama agent call with SSID context
- Logs all activity to `~/higgins_log.txt`
- Optionally triggers a subprocess script on connect
- Cross-platform: **Termux (Android)**, **Linux**, **Windows**

---

## Requirements

```bash
pip install requests
```

Termux also needs:
```bash
pkg install termux-api
```

---

## Config (top of script)

| Variable | Default | Description |
|---|---|---|
| `MODEL` | `qwen2.5:1.5b` | Ollama model |
| `POLL_INTERVAL` | `10` | Seconds between checks |
| `TRIGGER_SCRIPT` | `None` | Optional .py to run on connect |
| `LOG_FILE` | `~/higgins_log.txt` | Log output path |

---

## Run

```bash
python mrs_higgins.py
```

### Run as background service (Termux)
```bash
nohup python mrs_higgins.py &> ~/higgins_log.txt &
```

### Run on boot (add to startup.sh)
```bash
nohup python ~/mrs_higgins/mrs_higgins.py &
```

---

## Extending Her

`TRIGGER_SCRIPT` can point to any Python file — hook her into:
- `boardroom_start.py` — wake the boardroom on connect
- `molt_watchdog.py` — trigger a molt cycle
- `onboarding_agent.py` — check for pending LNbits payments
- Nostr DM relay check on reconnect

---

## Ecosystem Position

```
WiFi Event
    └─► mrs_higgins.py
            ├─► Ollama (qwen2.5:1.5b)
            ├─► higgins_log.txt
            └─► TRIGGER_SCRIPT (optional)
                    └─► boardroom / molt / nostr
```

---

*BleakNarratives — Vertical AI*
