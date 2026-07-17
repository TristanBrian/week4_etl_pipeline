#!/bin/bash
# ============================================================
# setup_cron.sh - Automatically installs the cron job
# Usage: bash setup_cron.sh
# ============================================================

# Get the absolute path of this script's directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$(which python3)"
CRON_CMD="0 9 * * * cd $PROJECT_DIR && $PYTHON_PATH $PROJECT_DIR/run_pipeline.py >> $PROJECT_DIR/cron_output.log 2>&1"

echo "=========================================="
echo "  ETL Pipeline - Cron Installer"
echo "=========================================="
echo "Project directory: $PROJECT_DIR"
echo "Python path:       $PYTHON_PATH"
echo ""
echo "Cron command to be added:"
echo "$CRON_CMD"
echo ""

# Check if the cron job already exists
if crontab -l 2>/dev/null | grep -q "$PROJECT_DIR/run_pipeline.py"; then
    echo "⚠️  Cron job already exists for this project."
    echo "   To remove it, run: crontab -e and delete the line."
    exit 0
fi

# Ask for confirmation
read -p "Do you want to add this cron job to run daily at 9:00 AM? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Add to crontab (preserve existing jobs)
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Cron job installed successfully!"
    echo "   Run 'crontab -l' to verify."
    echo "   Logs will be written to: $PROJECT_DIR/cron_output.log"
else
    echo "❌ Installation cancelled."
fi