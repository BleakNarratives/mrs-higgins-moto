# Author: BleakNarratives (Kevin Michael Talbert)
# Filename: main.py
# Extension: .py
# File Path: ~/Mrs-Higgins/backend/main.py
#
# Mrs. Higgins Backend — Full Swarm Brain
# FastAPI + Ollama + Hermes + Xenolang + Boardroom WebSocket
# Part of the Vertical AI / ZeroClaw ecosystem

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# ── Config ────────────────────────────────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_HOST",  "http://127.0.0.1:11434")
MODEL_DEFAULT = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
HERMES_BIN    = os.path.expanduser(os.getenv("HERMES_BIN", "~/build_hermes/bin/hermes"))
HERMESC_BIN   = os.path.expanduser(os.getenv("HERMESC_BIN", "~/build_hermes/bin/hermesc"))
ROOT_2026     = os.path.expanduser("~/root_2026")
LOG_FILE      = os.path.expanduser("~/Mrs-Higgins/backend/backend.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HIGGINS] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger("mrs_higgins")

# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Mrs. Higgins", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── Active WebSocket connections ──────────────────────────────────────────
boardroom_clients: list[WebSocket] = []

# ── Persona roster ────────────────────────────────────────────────────────
PERSONAS = {
    "dame_audrey":   {"model": MODEL_DEFAULT, "temp": 0.9,  "color": "#ff00bb"},
    "claiborne":     {"model": MODEL_DEFAULT, "temp": 0.75, "color": "#ff3300"},
    "chairman":      {"model": MODEL_DEFAULT, "temp": 0.6,  "color": "#ffcc00"},
    "zeroclaw":      {"model": MODEL_DEFAULT, "temp": 0.82, "color": "#00ff77"},
    "syntax":        {"model": MODEL_DEFAULT, "temp": 0.48, "color": "#00aaff"},
    "mrs_higgins":   {"model": MODEL_DEFAULT, "temp": 0.42, "color": "#ff8800"},
    "agent_6":       {"model": MODEL_DEFAULT, "temp": 0.79, "color": "#bb00ff"},
    "janebot":       {"model": MODEL_DEFAULT, "temp": 0.66, "color": "#ff6688"},
    "molt":          {"model": MODEL_DEFAULT, "temp": 0.54, "color": "#88ff00"},
    "vortex":        {"model": MODEL_DEFAULT, "temp": 0.87, "color": "#00ffcc"},
    "architect":     {"model": MODEL_DEFAULT, "temp": 0.51, "color": "#ffaa00"},
    "whorl":         {"model": MODEL_DEFAULT, "temp": 0.71, "color": "#ff44cc"},
}

# ── Xenolang opcode table ─────────────────────────────────────────────────
XENOLANG_OPCODES = {
    "AI": "analyze_input",
    "MB": "molt_begin",
    "ME": "molt_end",
    "BR": "boardroom_route",
    "AB": "abort_all",
    "WS": "ws_broadcast",
    "HX": "hermes_exec",
    "SM": "summon_persona",
    "YD": "yield_persona",
    "ST": "get_status",
}

# ── Ollama helper ─────────────────────────────────────────────────────────
async def ask_ollama(prompt: str, system: str = "", model: str = MODEL_DEFAULT,
                     temp: float = 0.7) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json={
                "model": model,
                "system": system,
                "prompt": prompt,
                "options": {"temperature": temp},
                "stream": False
            })
            return r.json().get("response", "[no response]").strip()
    except Exception as e:
        return f"[Ollama error: {e}]"

# ── Hermes execution ──────────────────────────────────────────────────────
def hermes_exec(js_code: str, timeout: int = 5) -> str:
    """Execute JS via local Hermes binary."""
    if not os.path.exists(HERMES_BIN):
        return f"[hermes not found at {HERMES_BIN}]"
    try:
        res = subprocess.run(
            [HERMES_BIN, "-eval", js_code],
            capture_output=True, text=True, timeout=timeout
        )
        return res.stdout.strip() if res.returncode == 0 else res.stderr.strip()
    except subprocess.TimeoutExpired:
        return "[hermes timeout]"
    except Exception as e:
        return f"[hermes error: {e}]"

def hermes_compile(js_path: str, hbc_path: str) -> bool:
    """Compile JS to HBC bytecode."""
    if not os.path.exists(HERMESC_BIN):
        return False
    try:
        res = subprocess.run(
            [HERMESC_BIN, "-emit-binary", "-out", hbc_path, js_path],
            capture_output=True, timeout=10
        )
        return res.returncode == 0
    except Exception:
        return False

# ── Xenolang decoder ──────────────────────────────────────────────────────
def xenolang_decode(message: str) -> tuple[str, str]:
    """Decode XL:OPCODE:payload → (opcode, payload)"""
    parts = message.split(":", 2)
    if len(parts) >= 2 and parts[0] == "XL":
        opcode  = parts[1].upper()
        payload = parts[2] if len(parts) > 2 else ""
        return opcode, payload
    return "", message

async def xenolang_dispatch(opcode: str, payload: str) -> str:
    """Route Xenolang opcode to handler."""
    handler = XENOLANG_OPCODES.get(opcode)
    if not handler:
        return f"[unknown opcode: {opcode}]"

    if opcode == "HX":
        return hermes_exec(payload)
    if opcode == "AB":
        await ws_broadcast({"action": "abort", "text": "ABORT signal received"})
        return "abort broadcast"
    if opcode == "ST":
        return json.dumps(await _build_status())
    if opcode == "AI":
        return await ask_ollama(payload)
    if opcode == "BR":
        return await boardroom_route(payload, None)
    return f"[{handler}: not yet wired]"

# ── WebSocket broadcast ───────────────────────────────────────────────────
async def ws_broadcast(message: dict):
    dead = []
    for ws in boardroom_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for d in dead:
        boardroom_clients.remove(d)

# ── Boardroom router ──────────────────────────────────────────────────────
async def boardroom_route(prompt: str, persona_key: Optional[str]) -> str:
    if persona_key and persona_key in PERSONAS:
        p = PERSONAS[persona_key]
        system = f"You are {persona_key.replace('_',' ').title()}, a persona in the Vertical AI boardroom. Stay in character. Be direct, opinionated, and brief."
        response = await ask_ollama(prompt, system=system, model=p["model"], temp=p["temp"])
        msg = {"persona": persona_key, "text": response,
               "temperature": p["temp"], "color": p["color"]}
        await ws_broadcast(msg)
        return response

    # No persona specified — pick based on prompt content
    lc = prompt.lower()
    if any(w in lc for w in ["object", "wrong", "no "]):
        key = "dame_audrey"
    elif any(w in lc for w in ["analyze", "syntax", "code"]):
        key = "syntax"
    elif any(w in lc for w in ["order", "chair", "vote"]):
        key = "chairman"
    elif any(w in lc for w in ["evolve", "molt", "improve"]):
        key = "molt"
    else:
        key = "zeroclaw"

    return await boardroom_route(prompt, key)

# ── Status builder ────────────────────────────────────────────────────────
async def _build_status() -> dict:
    hermes_ok = os.path.exists(HERMES_BIN)
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass

    modules = []
    if os.path.exists(ROOT_2026):
        try:
            modules = [d for d in os.listdir(ROOT_2026)
                       if os.path.isdir(os.path.join(ROOT_2026, d))
                       and any(f in os.listdir(os.path.join(ROOT_2026, d))
                               for f in ['start.sh', 'main.py'])]
        except Exception:
            pass

    return {
        "timestamp":    datetime.now().isoformat(),
        "hermes":       "ok" if hermes_ok else "missing",
        "ollama":       "ok" if ollama_ok else "offline",
        "model":        MODEL_DEFAULT,
        "ws_clients":   len(boardroom_clients),
        "personas":     len(PERSONAS),
        "modules":      modules,
    }

# ── Routes ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "Mrs. Higgins online", "version": "2.0.0"}

@app.get("/status")
async def status():
    return await _build_status()

@app.get("/income")
async def get_income():
    path = os.path.expanduser("~/income_summary.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"total": 0, "status": "no file found"}

@app.get("/audit")
async def audit_modules():
    if not os.path.exists(ROOT_2026):
        return {"error": "root_2026 not found", "path": ROOT_2026}
    try:
        modules = [d for d in os.listdir(ROOT_2026)
                   if os.path.isdir(os.path.join(ROOT_2026, d))
                   and any(f in os.listdir(os.path.join(ROOT_2026, d))
                           for f in ['start.sh', 'main.py'])]
        return {"shippable_modules": modules, "count": len(modules)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat")
async def chat(request: Request):
    data     = await request.json()
    msg      = data.get("message", {}).get("text", "hello")
    persona  = data.get("persona")
    response = await boardroom_route(msg, persona)
    return {"reply": response}

@app.post("/hermes")
async def hermes_endpoint(request: Request):
    data   = await request.json()
    js     = data.get("js", "print('no code provided');")
    result = hermes_exec(js)
    log.info("Hermes exec: %s", result[:80])
    return {"result": result}

@app.post("/xenolang")
async def xenolang_endpoint(request: Request):
    data    = await request.json()
    message = data.get("message", "")
    opcode, payload = xenolang_decode(message)
    if not opcode:
        return {"error": "invalid Xenolang message", "expected": "XL:OPCODE:payload"}
    result = await xenolang_dispatch(opcode, payload)
    return {"opcode": opcode, "result": result}

@app.post("/boardroom/{persona_key}")
async def boardroom_endpoint(persona_key: str, request: Request):
    data     = await request.json()
    prompt   = data.get("prompt", "")
    if persona_key not in PERSONAS:
        return {"error": f"unknown persona: {persona_key}",
                "available": list(PERSONAS.keys())}
    response = await boardroom_route(prompt, persona_key)
    return {"persona": persona_key, "response": response}

@app.get("/personas")
async def list_personas():
    return {"personas": list(PERSONAS.keys()), "count": len(PERSONAS)}

# ── WebSocket endpoint ────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    boardroom_clients.append(websocket)
    log.info("WS client connected. Total: %d", len(boardroom_clients))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                msg = {"type": "raw", "text": raw}

            t = msg.get("type", "")

            if t == "user_prompt" or t == "user_case":
                action  = msg.get("action", "argue")
                text    = msg.get("text", "")
                persona = msg.get("persona")
                response = await boardroom_route(text, persona)
                await websocket.send_json({
                    "type": "boardroom_response",
                    "text": response,
                    "action": action
                })

            elif t == "command":
                action = msg.get("action", "")
                if action == "abort":
                    await ws_broadcast({"action": "abort", "text": "ABORT"})
                elif action == "status":
                    s = await _build_status()
                    await websocket.send_json({"type": "status", **s})

            elif t == "xenolang":
                xmsg = msg.get("message", "")
                opcode, payload = xenolang_decode(xmsg)
                result = await xenolang_dispatch(opcode, payload)
                await websocket.send_json({"type": "xenolang_result",
                                           "opcode": opcode, "result": result})

    except WebSocketDisconnect:
        boardroom_clients.remove(websocket)
        log.info("WS client disconnected. Remaining: %d", len(boardroom_clients))

# ── Launch ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    log.info("Mrs. Higgins v2.0 starting...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
