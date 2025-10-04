#!/bin/bash
# Setup cron job to process offline queue every 15 minutes

# Path to the process script
SCRIPT_PATH="/home/collins/repos/pet-chip-reader/rfid_cam/scripts/process_offline_queue.py"
LOG_PATH="/home/collins/repos/pet-chip-reader/rfid_cam/offline_queue_processing.log"

# Create cron job entry
CRON_ENTRY="*/15 * * * * /usr/bin/python3 $SCRIPT_PATH >> $LOG_PATH 2>&1"

echo "Setting up cron job for offline queue processing..."

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "process_offline_queue.py"; then
    echo "Cron job already exists. Current cron jobs:"
    crontab -l | grep process_offline_queue
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✓ Cron job added successfully!"
    echo "The offline queue will now be processed automatically every 15 minutes."
fi

echo ""
echo "Current cron jobs:"
crontab -l

echo ""
echo "To manually run the queue processor:"
echo "  $SCRIPT_PATH"
echo ""
echo "To run in dry-run mode (see what would be processed):"
echo "  $SCRIPT_PATH --dry-run"
echo ""
echo "To view processing logs:"
echo "  tail -f $LOG_PATH"
echo ""
echo "To remove the cron job:"
echo "  crontab -l | grep -v process_offline_queue.py | crontab -"