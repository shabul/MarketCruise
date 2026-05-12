#!/bin/bash
# Sets up macOS crontab entries for MarketCruise.
# Prerequisites: MarketCruise server must be running (python main.py --server)
# Run: bash cron_setup.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

SERVER_URL="http://localhost:8001"

CRON_ENTRIES=(
  "0 7  * * 1   curl -s -X POST $SERVER_URL/run/weekly  >> $LOG_DIR/weekly.log 2>&1"
  "0 8  * * 1-5 curl -s -X POST $SERVER_URL/run/morning >> $LOG_DIR/morning.log 2>&1"
  "0 14 * * 1-5 curl -s -X POST $SERVER_URL/run/midday  >> $LOG_DIR/midday.log 2>&1"
  "0 22 * * 1-5 curl -s -X POST $SERVER_URL/run/evening >> $LOG_DIR/evening.log 2>&1"
)

# Remove old MarketCruise entries
TMP=$(mktemp)
crontab -l 2>/dev/null | grep -v "marketcruise\|$SERVER_URL" > "$TMP"

# Add new entries with a marker comment
echo "# MarketCruise" >> "$TMP"
for entry in "${CRON_ENTRIES[@]}"; do
  echo "$entry" >> "$TMP"
done

crontab "$TMP"
rm "$TMP"

echo "Crontab updated. Current MarketCruise entries:"
crontab -l | grep -A4 "MarketCruise"
echo ""
echo "Note: Ensure 'python main.py --server' is running before cron jobs fire."
echo "To auto-start at login, add a macOS LaunchAgent (see README)."
