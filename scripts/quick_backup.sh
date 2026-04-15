#!/bin/bash
# Quick backup script - Run this anytime to backup your database

echo "================================"
echo "Quick Database Backup"
echo "================================"
echo "Time: $(date)"
echo ""

# Activate virtual environment
source venv/bin/activate

# Run backup
python3 scripts/backup_database_to_csv.py

echo ""
echo "================================"
echo "Backup files location:"
echo "  data/backups/"
echo ""
echo "To restore:"
echo "  python3 scripts/restore_from_backup.py --file data/backups/all_data_backup_TIMESTAMP.csv"
echo "================================"
