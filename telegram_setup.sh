#!/usr/bin/env bash
# Author: BleakNarratives
# Filename: telegram_setup.sh
# Path: /storage/ED7B-AD5A/root_2026/moto-2024-sd-r26/telegram_setup.sh
#
# One-time Telegram setup. Gets your bot token and chat ID,
# writes them to front_desk_config.json and ~/.bashrc permanently.

CONFIG="/storage/ED7B-AD5A/root_2026/moto-2024-sd-r26/front_desk_config.json"

echo ""
echo "════════════════════════════════════════"
echo "  Telegram Setup — Mrs. Higgins"
echo "════════════════════════════════════════"
echo ""
echo "Step 1: Get your bot token"
echo "  → Open Telegram"
echo "  → Search for @BotFather"
echo "  → Send: /newbot"
echo "  → Follow prompts, copy the token it gives you"
echo ""
read -p "Paste your TELEGRAM_BOT_TOKEN here: " BOT_TOKEN

echo ""
echo "Step 2: Get your Chat ID"
echo "  → Send any message to your new bot in Telegram"
echo "  → We'll fetch your chat ID automatically..."
echo ""

CHAT_ID=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" | \
  python3 -c "
import json,sys
data=json.load(sys.stdin)
results=data.get('result',[])
if results:
    print(results[-1]['message']['chat']['id'])
else:
    print('NOT_FOUND')
")

if [ "$CHAT_ID" = "NOT_FOUND" ]; then
  echo "  Could not auto-detect. Send a message to your bot first, then re-run."
  echo "  Or paste your chat ID manually:"
  read -p "  TELEGRAM_CHAT_ID: " CHAT_ID
else
  echo "  ✓ Chat ID detected: $CHAT_ID"
fi

echo ""
echo "Step 3: Writing to config and environment..."

# Write to .bashrc
echo "" >> ~/.bashrc
echo "# Telegram — Mrs. Higgins" >> ~/.bashrc
echo "export TELEGRAM_BOT_TOKEN=\"$BOT_TOKEN\"" >> ~/.bashrc
echo "export TELEGRAM_CHAT_ID=\"$CHAT_ID\"" >> ~/.bashrc

# Write to config.json
if [ -f "$CONFIG" ]; then
  python3 - << PYEOF
import json
with open("$CONFIG") as f:
    c = json.load(f)
c["telegram_bot_token"] = "$BOT_TOKEN"
c["telegram_chat_id"] = "$CHAT_ID"
with open("$CONFIG", "w") as f:
    json.dump(c, f, indent=2)
print("  ✓ Config updated")
PYEOF
fi

# Apply to current session
export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
export TELEGRAM_CHAT_ID="$CHAT_ID"

# Test it
echo ""
echo "Step 4: Sending test message..."
RESULT=$(curl -s -X POST \
  "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"${CHAT_ID}\",\"text\":\"✅ Mrs. Higgins is online. Telegram confirmed.\"}")

if echo "$RESULT" | grep -q '"ok":true'; then
  echo "  ✓ Test message sent — check Telegram"
else
  echo "  ✗ Something went wrong. Check your token and try again."
  echo "  Response: $RESULT"
fi

echo ""
echo "════════════════════════════════════════"
echo "  DONE. Run: source ~/.bashrc"
echo "  Then: python the_closer.py"
echo "════════════════════════════════════════"
echo ""
