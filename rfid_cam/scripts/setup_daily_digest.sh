#!/bin/bash
# Setup cron job for daily digest emails

# Path to the daily digest script
SCRIPT_PATH="/home/collins/repos/pet-chip-reader/rfid_cam/scripts/generate_daily_digest.py"
LOG_PATH="/home/collins/repos/pet-chip-reader/rfid_cam/daily_digest.log"

# Create cron job entry for 6:00 PM daily
CRON_ENTRY="0 18 * * * /usr/bin/python3 $SCRIPT_PATH >> $LOG_PATH 2>&1"

echo "Setting up daily digest email cron job..."

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "generate_daily_digest.py"; then
    echo "Daily digest cron job already exists. Current cron jobs:"
    crontab -l | grep generate_daily_digest
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✓ Daily digest cron job added successfully!"
    echo "Daily digest emails will be sent to dccollins@gmail.com every day at 6:00 PM."
fi

echo ""
echo "Current cron jobs:"
crontab -l

echo ""
echo "Manual commands:"
echo "  Test today's digest (dry-run):    $SCRIPT_PATH --dry-run"
echo "  Send today's digest now:          $SCRIPT_PATH" 
echo "  Generate digest for specific date: $SCRIPT_PATH --date 2025-10-03"
echo ""
echo "View digest logs:"
echo "  tail -f $LOG_PATH"
echo ""
echo "Remove daily digest cron job:"
echo "  crontab -l | grep -v generate_daily_digest.py | crontab -"