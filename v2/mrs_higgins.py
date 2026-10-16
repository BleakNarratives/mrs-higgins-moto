# Author: BleakNarratives (Kevin Michael Talbert)
# Filename: mrs_higgins.py
# Extension: .py
# File Path: ~/mrs_higgins/mrs_higgins.py
#
# Mrs. Higgins — WiFi-triggered real-world interface agent
# Part of the Vertical AI / ZeroClaw ecosystem
# Monitors WiFi connection state and triggers Ollama-backed agent on connect

import subprocess
import time
import json
import requests
import logging
import platform
import os
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL     = "http://localhost:11434/api/generate"
MODEL          = "qwen2.5:1.5b"
LOG_FILE       = os.path.expanduser("~/higgins_log.txt")
POLL_INTERVAL  = 10  # seconds between wifi checks
TRIGGER_SCRIPT = None  # optional: path to script to run on connect

SYSTEM_PROMPT = """You are Mrs. Higgins — the real-world interface layer of the Vertical AI ecosystem.
You activate whenever this device connects to a network. Your job is to assess the environment,
report status, and flag anything requiring attention from the boardroom. Be terse, precise, and watchful.
You are the eyes and ears on the ground."""

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HIGGINS] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("mrs_higgins")

# ── WiFi Detection ────────────────────────────────────────────────────────────
def get_wifi_status():
    """Returns (connected: bool, ssid: str) cross-platform."""
    system = platform.system()

    try:
        if system == "Linux":
            # Termux / Android
            if os.path.exists("/data/data/com.termux"):
                result = subprocess.run(
                    ["termux-wifi-connectioninfo"],
                    capture_output=True, text=True, timeout=5
                )
                data = json.loads(result.stdout)
                ssid = data.get("ssid", "")
                return bool(ssid and ssid != "<unknown ssid>"), ssid
            # Standard Linux
            result = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if line.startswith("yes:"):
                    return True, line.split(":")[1]
            return False, ""

        elif system == "Windows":
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=5
            )
            connected = "State" in result.stdout and "connected" in result.stdout
            ssid = ""
            for line in result.stdout.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    ssid = line.split(":")[1].strip()
                    break
            return connected, ssid

    except Exception as e:
        log.warning(f"WiFi check failed: {e}")
        return False, ""

    return False, ""

# ── Ollama Agent Call ─────────────────────────────────────────────────────────
def call_higgins(ssid: str, context: str = "") -> str:
    prompt = f"Device just connected to network: '{ssid}'. {context} Assess and report."
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False
        }, timeout=30)
        data = response.json()
        return data.get("response", "[no response]")
    except Exception as e:
        return f"[Ollama unreachable: {e}]"

# ── Optional trigger script ───────────────────────────────────────────────────
def run_trigger():
    if TRIGGER_SCRIPT and os.path.exists(TRIGGER_SCRIPT):
        try:
            subprocess.Popen(["python", TRIGGER_SCRIPT])
            log.info(f"Trigger script fired: {TRIGGER_SCRIPT}")
        except Exception as e:
            log.warning(f"Trigger script failed: {e}")

# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    log.info("Mrs. Higgins online. Watching for WiFi...")
    last_state = False

    while True:
        connected, ssid = get_wifi_status()

        if connected and not last_state:
            log.info(f"WiFi connected: {ssid}")
            response = call_higgins(ssid)
            log.info(f"Higgins says: {response}")
            run_trigger()

        elif not connected and last_state:
            log.info("WiFi disconnected. Standing by.")

        last_state = connected
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
