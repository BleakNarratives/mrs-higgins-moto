# Author: BleakNarratives
# Filename: front_desk_lady.py
# Path: /storage/ED7B-AD5A/root_2026/moto-2024-sd-r26/front_desk_lady.py

import json
import os
import sys
import argparse
import urllib.request
import urllib.error

# Front Desk Lady — Mrs. Higgins
# Autonomously routes SaaS packages to endpoints for passive income.
# Invoice backend: Voltage Payments API
# She doesn't accept excuses. She ships.

VOLTAGE_URL = "https://payments.voltage.cloud"

class FrontDeskLady:
    def __init__(self, lightning_account_id=None, voltage_api_key=None, dry_run=False):
        self.lightning_account_id = lightning_account_id
        self.voltage_api_key = voltage_api_key
        self.dry_run = dry_run
        self.packages = []
        self.routing_log = []

    def load_packages(self, directory):
        if not os.path.exists(directory):
            print(f"[ERROR] Directory {directory} does not exist.")
            return
        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(directory, filename), "r") as f:
                        pkg = json.load(f)
                        self.packages.append(pkg)
                        print(f"[LOADED] {filename}")
                except Exception as e:
                    print(f"[SKIP] {filename}: {e}")

    def create_voltage_invoice(self, package):
        """
        POST to Voltage Payments API to create a Lightning invoice.
        Returns (payment_request, payment_id) or (None, None) on failure.
        """
        if not self.voltage_api_key:
            return None, None

        amount_sats = int(package.get("price_sats", 1000))
        memo = f"Vertical AI: {package.get('name', 'SaaS Package')}"

        payload = json.dumps({
            "amount": amount_sats,
            "description": memo,
            "currency": "BTC",
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{VOLTAGE_URL}/api/v1/invoices",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.voltage_api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data.get("payment_request"), data.get("id")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  [Voltage] HTTP {e.code}: {body[:120]}")
            return None, None
        except Exception as e:
            print(f"  [Voltage] Error: {e}")
            return None, None

    def route_package(self, package, platform_filter=None):
        name = package.get("name", "Unnamed")
        print(f"\n[ROUTING] {name}")
        platforms = package.get("target_platforms", ["Fiverr", "Upwork"])
        if platform_filter:
            platforms = [p for p in platforms if p.lower() == platform_filter.lower()]
            if not platforms:
                print(f"  [SKIP] No match for platform filter '{platform_filter}'")
                return

        invoice_bolt11, payment_id = None, None
        if not self.dry_run:
            invoice_bolt11, payment_id = self.create_voltage_invoice(package)
            if invoice_bolt11:
                print(f"  [Voltage] Invoice created (id: {str(payment_id)[:12]}...)")
            else:
                print(f"  [Voltage] No invoice — check API key or connectivity")

        for platform in platforms:
            summary = self.generate_markdown_summary(package, platform, invoice_bolt11)
            self.routing_log.append({
                "package_name": name,
                "platform": platform,
                "status": "DRY_RUN" if self.dry_run else "Routed",
                "payment_id": payment_id,
                "invoice_bolt11": invoice_bolt11,
                "summary": summary
            })
            tag = "[DRY]" if self.dry_run else "[OK]"
            print(f"  {tag} → {platform}")

    def generate_markdown_summary(self, package, platform, invoice_bolt11=None):
        lines = [
            f"### [New SaaS Offering] {package['name']} on {platform}",
            "",
            f"**Tagline:** {package.get('tagline', '')}",
            "",
            f"**Description:** {package.get('description', '')}",
            "",
            "**Key Features:**",
        ]
        for feature in package.get("features", []):
            lines.append(f"- {feature}")
        lines += [
            "",
            f"**Pricing:** {package.get('pricing_model', '')}",
            f"**Estimated ROI:** {package.get('estimated_roi_per_business', '')}",
            "",
            "**Payment Method:** Lightning Network (BTC)",
            f"**Lightning Address:** {self.lightning_account_id or 'NOT CONFIGURED'}",
        ]
        if invoice_bolt11:
            lines.append(f"**BOLT11 Invoice:** `{invoice_bolt11}`")
        return "\n".join(lines)

    def run(self, platform_filter=None):
        if not self.packages:
            print("[ABORT] No packages loaded.")
            return
        mode = "DRY RUN" if self.dry_run else "LIVE"
        print(f"\n=== Mrs. Higgins ON DUTY [{mode}] — {len(self.packages)} package(s) ===")
        for package in self.packages:
            self.route_package(package, platform_filter=platform_filter)
        self.save_routing_log()

    def save_routing_log(self):
        log_path = "front_desk_routing_log.json"
        with open(log_path, "w") as f:
            json.dump(self.routing_log, f, indent=2)
        print(f"\n[DONE] {len(self.routing_log)} route(s) logged → {log_path}")


def main():
    parser = argparse.ArgumentParser(description="Front Desk Lady — SaaS package router")
    parser.add_argument("--packages-dir", default="./saas_packages")
    parser.add_argument("--platform", default=None, help="Fiverr | Upwork | Nostr")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = {}
    if os.path.exists("front_desk_config.json"):
        with open("front_desk_config.json", "r") as f:
            config = json.load(f)

    lightning_id    = os.getenv("LIGHTNING_ACCOUNT_ID", config.get("lightning_account_id"))
    voltage_api_key = os.getenv("VOLTAGE_API_KEY",      config.get("voltage_api_key"))

    if not voltage_api_key:
        print("[WARN] No Voltage API key. Invoices will be skipped.")
        print("       Set voltage_api_key in front_desk_config.json or VOLTAGE_API_KEY env var.")

    fdl = FrontDeskLady(lightning_id, voltage_api_key, dry_run=args.dry_run)
    fdl.load_packages(args.packages_dir)
    fdl.run(platform_filter=args.platform)


if __name__ == "__main__":
    main()
