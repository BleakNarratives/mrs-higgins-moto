#!/usr/bin/env python3
# Author: BleakNarratives
# Filename: webhook_router.py
# Path: /storage/ED7B-AD5A/root_2026/moto-2024-sd-r26/webhook_router.py
#
# Nervous system for the Vertical AI ecosystem.
# Receives GitHub webhook events, routes them to the right crew member.
#
# Events handled:
#   push        → molt (trigger arena/improvement run)
#   issues      → Claude API triage + Telegram alert
#   star        → zeroclaw Nostr broadcast
#   pull_request → Claude API review
#
# Setup:
#   pip install flask --break-system-packages
#   python webhook_router.py
#   # Then expose via: cloudflared tunnel --url http://localhost:7777
#   # Point GitHub webhook to: https://your-tunnel.trycloudflare.com/webhook

import json
import os
import subprocess
import hashlib
import hmac
import urllib.request
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_SECRET  = os.getenv("GITHUB_WEBHOOK_SECRET", "")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT   = os.getenv("TELEGRAM_CHAT_ID", "")
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
ZEROCLAW_PATH   = os.getenv("ZEROCLAW_PATH", "/data/data/com.termux/files/home/.local/bin/zeroclaw")
MOLT_PATH       = os.getenv("MOLT_PATH", "/storage/ED7B-AD5A/root_2026/molt_watchdog.py")
LOG_PATH        = "webhook_log.json"

# ── Helpers ──────────────────────────────────────────────────

def log_event(event_type, payload, action_taken):
    entry = {
        "time": datetime.utcnow().isoformat() + "Z",
        "event": event_type,
        "action": action_taken,
        "repo": payload.get("repository", {}).get("full_name", "unknown")
    }
    log = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            log = json.load(f)
    log.append(entry)
    with open(LOG_PATH, "w") as f:
        json.dump(log[-200:], f, indent=2)  # keep last 200

def verify_signature(payload_bytes, sig_header):
    if not WEBHOOK_SECRET:
        return True  # skip verification if no secret set
    mac = hmac.new(WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, sig_header or "")

def telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[Telegram] {e}")

def claude_respond(prompt, max_tokens=500):
    """Uses local Ollama instead of paid Anthropic API."""
    ollama_url   = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    payload = json.dumps({
        "model": ollama_model,
        "prompt": prompt,
        "stream": False
    }).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except Exception as e:
        print(f"[Ollama] {e}")
        return None

def post_github_comment(repo, issue_number, body, token):
    if not token:
        return
    payload = json.dumps({"body": body}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        data=payload,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mrs-Higgins-Webhook"
        },
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[GitHub] {e}")

def run_molt():
    try:
        subprocess.Popen(
            ["python", MOLT_PATH],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("[MOLT] Triggered")
        return "molt triggered"
    except Exception as e:
        print(f"[MOLT] {e}")
        return f"molt failed: {e}"

def run_zeroclaw(message):
    try:
        subprocess.Popen(
            [ZEROCLAW_PATH, "broadcast", message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("[ZEROCLAW] Broadcast triggered")
        return "zeroclaw broadcast"
    except Exception as e:
        print(f"[ZEROCLAW] {e}")
        return f"zeroclaw failed: {e}"

# ── Event handlers ───────────────────────────────────────────

def handle_push(payload):
    repo    = payload.get("repository", {}).get("full_name", "unknown")
    branch  = payload.get("ref", "").replace("refs/heads/", "")
    pusher  = payload.get("pusher", {}).get("name", "unknown")
    commits = len(payload.get("commits", []))
    msg     = f"📦 Push to `{repo}` ({branch}) — {commits} commit(s) by {pusher}"

    telegram(msg)
    action = run_molt()
    return action

def handle_issue(payload, github_token):
    action  = payload.get("action")
    issue   = payload.get("issue", {})
    repo    = payload.get("repository", {}).get("full_name", "unknown")
    number  = issue.get("number")
    title   = issue.get("title", "")
    body    = issue.get("body", "")
    user    = issue.get("user", {}).get("login", "unknown")

    if action != "opened":
        return "ignored"

    telegram(f"🐛 New issue on `{repo}` #{number}\n*{title}*\nBy: {user}")

    prompt = (
        f"You are Mrs. Higgins, a no-nonsense AI assistant for the Vertical AI project "
        f"by BleakNarratives. Someone opened a GitHub issue on the repo '{repo}'.\n\n"
        f"Issue #{number}: {title}\n{body}\n\n"
        f"Write a brief, helpful response. Be direct. Max 3 sentences."
    )
    response = claude_respond(prompt)
    if response and github_token:
        post_github_comment(repo, number, response, github_token)
        return "claude responded"
    return "no response posted"

def handle_star(payload):
    repo   = payload.get("repository", {}).get("full_name", "unknown")
    stars  = payload.get("repository", {}).get("stargazers_count", "?")
    user   = payload.get("sender", {}).get("login", "unknown")
    action = payload.get("action")

    if action != "created":
        return "ignored"

    msg = f"⭐ {user} starred {repo} — total: {stars}"
    telegram(msg)

    nostr_msg = f"⭐ {repo} just got starred by {user} ({stars} total) — bleaknarratives@speed.app"
    run_zeroclaw(nostr_msg)
    return "star handled"

def handle_pr(payload, github_token):
    action = payload.get("action")
    pr     = payload.get("pull_request", {})
    repo   = payload.get("repository", {}).get("full_name", "unknown")
    number = pr.get("number")
    title  = pr.get("title", "")
    body   = pr.get("body", "")

    if action != "opened":
        return "ignored"

    telegram(f"🔀 New PR on `{repo}` #{number}: *{title}*")

    prompt = (
        f"You are a code reviewer for the Vertical AI project by BleakNarratives. "
        f"A pull request was opened on '{repo}'.\n\n"
        f"PR #{number}: {title}\n{body}\n\n"
        f"Write a brief review acknowledgment. Be direct. Max 2 sentences."
    )
    response = claude_respond(prompt)
    if response and github_token:
        post_github_comment(repo, number, response, github_token)
        return "pr acknowledged"
    return "no response"

# ── Route ────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    payload_bytes = request.get_data()

    if not verify_signature(payload_bytes, request.headers.get("X-Hub-Signature-256")):
        return jsonify({"error": "invalid signature"}), 401

    event   = request.headers.get("X-GitHub-Event", "unknown")
    payload = request.get_json(force=True) or {}
    github_token = os.getenv("GITHUB_TOKEN", "")

    print(f"[EVENT] {event}")

    if event == "push":
        action = handle_push(payload)
    elif event == "issues":
        action = handle_issue(payload, github_token)
    elif event == "star":
        action = handle_star(payload)
    elif event == "pull_request":
        action = handle_pr(payload, github_token)
    elif event == "ping":
        action = "pong"
        print("[PING] GitHub connected successfully")
    else:
        action = f"unhandled event: {event}"

    log_event(event, payload, action)
    return jsonify({"status": "ok", "action": action})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Mrs. Higgins is on duty"})

# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", "7777"))
    print(f"""
╔══════════════════════════════════════════╗
║   WEBHOOK ROUTER — Vertical AI           ║
║   Listening on port {port}                  ║
║                                          ║
║   Expose with:                           ║
║   cloudflared tunnel --url               ║
║     http://localhost:{port}                 ║
║                                          ║
║   Then set GitHub webhook URL to:        ║
║   https://xxxx.trycloudflare.com/webhook ║
╚══════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
