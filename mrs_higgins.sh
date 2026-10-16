#!/usr/bin/env bash
# Author: BleakNarratives
# Filename: mrs_higgins.sh
# Path: G:\Foxwood\moto-2024-sd-r26\mrs_higgins.sh
# Usage: bash mrs_higgins.sh [--dry-run] [--platform Fiverr]

set -euo pipefail

DRY=""
PLATFORM=""
LOG_DIR="./logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/run_$TIMESTAMP.log"

mkdir -p "$LOG_DIR"

for arg in "$@"; do
  case $arg in
    --dry-run)  DRY="--dry-run" ;;
    --platform) shift; PLATFORM="--platform $1" ;;
  esac
done

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_FILE"; }
die() { log "FATAL: $*"; exit 1; }

log "=== Mrs. Higgins Pipeline START ==="
log "Mode: ${DRY:-LIVE} | Platform: ${PLATFORM:-ALL}"

log "--- 1/5 Front Desk Lady ---"
python front_desk_lady.py $DRY $PLATFORM 2>&1 | tee -a "$LOG_FILE" || die "front_desk_lady.py failed"

log "--- 2/5 Bookkeeper ---"
python bookkeeper.py 2>&1 | tee -a "$LOG_FILE" || log "WARN: bookkeeper.py failed (non-fatal)"

log "--- 3/5 The Closer ---"
python the_closer.py 2>&1 | tee -a "$LOG_FILE" || log "WARN: the_closer.py failed (non-fatal)"

log "--- 4/5 Copywriter ---"
python copywriter.py $DRY $PLATFORM 2>&1 | tee -a "$LOG_FILE" || log "WARN: copywriter.py failed (non-fatal)"

log "--- 5/5 Scout ---"
if [ -f scout.py ]; then
  python scout.py 2>&1 | tee -a "$LOG_FILE" || log "WARN: scout.py failed (non-fatal)"
elif [ -f scout_v2.py ]; then
  python scout_v2.py 2>&1 | tee -a "$LOG_FILE" || log "WARN: scout_v2.py failed (non-fatal)"
else
  log "WARN: no scout script found (scout.py or scout_v2.py)"
fi

log "=== Pipeline COMPLETE → $LOG_FILE ==="
