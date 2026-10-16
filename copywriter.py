# Author: BleakNarratives
# Filename: copywriter.py
# Path: G:\Foxwood\moto-2024-sd-r26\copywriter.py

import json
import os
import sys
import argparse
import urllib.request
import urllib.error

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
OUTPUT_DIR   = "copy_output"

PLATFORM_PROMPTS = {
    "Fiverr": (
        "You are a Fiverr gig copywriter. Write a punchy Fiverr gig listing. "
        "Include: Gig Title (max 80 chars), a 3-sentence Description, "
        "3 bullet FAQs, and a clear call to action. Keep it casual and outcome-focused."
    ),
    "Upwork": (
        "You are an Upwork proposal writer. Write a professional Upwork job proposal. "
        "Include: opening hook (1 sentence), what you offer (2-3 sentences), "
        "specific deliverables list, and a closing CTA. Tone: competent, direct, no fluff."
    ),
    "Nostr": (
        "You are writing a Nostr zap post to promote a SaaS product. "
        "Max 280 characters. Lightning-native audience. Be terse, technical, and real. "
        "Include the product name and a lightning payment hook. No hashtag spam."
    ),
}

def ollama_generate(prompt, model=OLLAMA_MODEL):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except Exception as e:
        print(f"  [Ollama] Error: {e}")
        return None

def generate_copy(package, platform):
    system = PLATFORM_PROMPTS.get(platform, PLATFORM_PROMPTS["Fiverr"])
    user_block = (
        f"Product Name: {package.get('name', 'Unnamed')}\n"
        f"Tagline: {package.get('tagline', '')}\n"
        f"Description: {package.get('description', '')}\n"
        f"Features: {', '.join(package.get('features', []))}\n"
        f"Pricing: {package.get('pricing_model', '')}\n"
        f"Estimated ROI: {package.get('estimated_roi_per_business', '')}"
    )
    prompt = f"{system}\n\n---\n{user_block}\n---\n\nWrite the copy now:"
    return ollama_generate(prompt)

def run(packages_dir="./saas_packages", platform_filter=None, dry_run=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(packages_dir):
        print(f"[ABORT] {packages_dir} not found.")
        return

    packages = []
    for fname in sorted(os.listdir(packages_dir)):
        if fname.endswith(".json"):
            with open(os.path.join(packages_dir, fname), "r") as f:
                packages.append(json.load(f))

    if not packages:
        print("[ABORT] No packages found.")
        return

    print(f"[COPYWRITER] model={OLLAMA_MODEL} packages={len(packages)}")

    for pkg in packages:
        name = pkg.get("name", "unnamed")
        platforms = pkg.get("target_platforms", ["Fiverr", "Upwork"])
        if platform_filter:
            platforms = [p for p in platforms if p.lower() == platform_filter.lower()]

        for platform in platforms:
            slug = name.lower().replace(" ", "_")
            out_path = os.path.join(OUTPUT_DIR, f"{slug}_{platform.lower()}.md")
            print(f"  [{platform}] {name}...", end=" ", flush=True)

            if dry_run:
                print("[DRY]")
                continue

            copy = generate_copy(pkg, platform)
            if copy:
                with open(out_path, "w") as f:
                    f.write(f"# {name} — {platform}\n\n{copy}\n")
                print(f"[SAVED] → {out_path}")
            else:
                print("[FAIL]")

    print(f"\n[DONE] Copy files in ./{OUTPUT_DIR}/")

def main():
    parser = argparse.ArgumentParser(description="Copywriter — Ollama-powered platform copy generator")
    parser.add_argument("--packages-dir", default="./saas_packages")
    parser.add_argument("--platform", default=None, help="Fiverr | Upwork | Nostr")
    parser.add_argument("--model", default=None, help="Override Ollama model")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.model:
        global OLLAMA_MODEL
        OLLAMA_MODEL = args.model

    run(args.packages_dir, args.platform, args.dry_run)

if __name__ == "__main__":
    main()
