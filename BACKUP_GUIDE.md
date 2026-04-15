# Database Backup Guide

## Overview

Your database data is now safely backed up to CSV files. This provides protection against:
- Database corruption
- Accidental data deletion
- System failures
- Migration to new database

## Backup Summary

**Date:** April 15, 2026 at 12:10 PM
**Total Data:** 66,430 candles (5.10 MB)
**Symbols:** 7 (NIFTY50, BANKNIFTY, RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK)
**Date Range:** October 13, 2025 to April 15, 2026

## Files Created

### 1. Complete Backup
- **File:** `data/backups/all_data_backup_20260415_121003.csv`
- **Size:** 5.10 MB
- **Contains:** All 66,430 candles from all symbols
- **Use:** Full database restore

### 2. Individual Symbol Backups
Each symbol has its own backup file:
- `NIFTY50_backup_20260415_121005.csv` (9,574 candles, 783 KB)
- `BANKNIFTY_backup_20260415_121005.csv` (9,476 candles, 799 KB)
- `RELIANCE_backup_20260415_121005.csv` (9,476 candles, 743 KB)
- `TCS_backup_20260415_121005.csv` (9,476 candles, 698 KB)
- `HDFCBANK_backup_20260415_121005.csv` (9,476 candles, 743 KB)
- `INFY_backup_20260415_121005.csv` (9,476 candles, 706 KB)
- `ICICIBANK_backup_20260415_121005.csv` (9,476 candles, 753 KB)

### 3. Manifest File
- **File:** `backup_manifest_20260415_121006.txt`
- **Contains:** Backup metadata, statistics, and restore instructions

## How to Use Backups

### Create New Backup
```bash
# Backup all data
python3 scripts/backup_database_to_csv.py

# Backup to custom directory
python3 scripts/backup_database_to_csv.py --output data/backups/2026-04-15
```

### Restore from Backup

#### Option 1: Restore All Data
```bash
python3 scripts/restore_from_backup.py --file data/backups/all_data_backup_20260415_121003.csv
```

#### Option 2: Restore Specific Symbol
```bash
python3 scripts/restore_from_backup.py --file data/backups/NIFTY50_backup_20260415_121005.csv
```

#### Option 3: Restore Multiple Files
```bash
python3 scripts/restore_from_backup.py --directory data/backups --pattern "*_backup_*.csv"
```

#### Option 4: Clear and Restore
```bash
# This will delete existing data for symbols in the backup before restoring
python3 scripts/restore_from_backup.py --file data/backups/all_data_backup_20260415_121003.csv --clear
```

### Direct PostgreSQL Restore
```bash
# Using psql COPY command
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "
COPY ohlcv_intraday(time, symbol, exchange, interval, open, high, low, close, volume)
FROM '/absolute/path/to/data/backups/all_data_backup_20260415_121003.csv'
WITH (FORMAT csv, HEADER true);
"
```

## Backup Strategy

### Daily Backups
Create a daily backup to track data growth:
```bash
# Add to crontab for daily backup at 6 PM
0 18 * * * cd /home/ts/MIG/prod-grade && source venv/bin/activate && python3 scripts/backup_database_to_csv.py --output data/backups/daily/$(date +\%Y-\%m-\%d)
```

### Weekly Backups
Keep weekly backups for longer-term safety:
```bash
# Weekly backup every Sunday at 11 PM
0 23 * * 0 cd /home/ts/MIG/prod-grade && source venv/bin/activate && python3 scripts/backup_database_to_csv.py --output data/backups/weekly/$(date +\%Y-\%W)
```

### Before Major Changes
Always backup before:
- Database schema changes
- Major data imports
- System upgrades
- Testing new features

## File Format

CSV files contain the following columns:
- `time` - Timestamp (with timezone)
- `symbol` - Trading symbol
- `exchange` - Exchange name (NSE)
- `interval` - Candle interval (5m)
- `open` - Open price
- `high` - High price
- `low` - Low price
- `close` - Close price
- `volume` - Trading volume

## Storage Recommendations

### Local Storage
- Keep at least 3 recent backups
- Store in `data/backups/` directory
- Total size: ~5-10 MB per backup

### External Storage
Consider copying backups to:
1. **External Drive:** USB drive or external HDD
2. **Cloud Storage:** Google Drive, Dropbox, OneDrive
3. **Network Storage:** NAS or network drive
4. **Git Repository:** For version control (if size permits)

### Backup Rotation
```bash
# Keep last 7 daily backups
find data/backups/daily -type f -mtime +7 -delete

# Keep last 4 weekly backups
find data/backups/weekly -type f -mtime +28 -delete
```

## Verification

### Verify Backup Integrity
```bash
# Check file exists and has data
ls -lh data/backups/all_data_backup_*.csv

# Count rows (should match candle count + 1 for header)
wc -l data/backups/all_data_backup_20260415_121003.csv

# View first few rows
head -n 5 data/backups/all_data_backup_20260415_121003.csv
```

### Test Restore
```bash
# Test restore to verify backup works
# (This won't overwrite existing data due to ON CONFLICT DO NOTHING)
python3 scripts/restore_from_backup.py --file data/backups/all_data_backup_20260415_121003.csv
```

## Troubleshooting

### Backup Failed
1. Check database connection
2. Verify disk space: `df -h`
3. Check permissions: `ls -la data/backups/`
4. Review error logs

### Restore Failed
1. Verify CSV file exists and is readable
2. Check database connection
3. Ensure table schema matches
4. Check for data type mismatches

### Large File Size
If backups become too large:
1. Compress files: `gzip data/backups/*.csv`
2. Archive old data
3. Use incremental backups
4. Consider database-native backup tools

## Emergency Recovery

If database is lost or corrupted:

1. **Stop all services:**
   ```bash
   # Stop live trading
   pkill -f start_live_trading
   ```

2. **Restore database:**
   ```bash
   # Recreate database if needed
   PGPASSWORD=postgres psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS algotrading;"
   PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE algotrading;"
   
   # Run schema migrations
   # (Your schema creation scripts here)
   
   # Restore data
   python3 scripts/restore_from_backup.py --file data/backups/all_data_backup_20260415_121003.csv
   ```

3. **Verify data:**
   ```bash
   python3 scripts/verify_data_collection.py
   ```

4. **Restart services:**
   ```bash
   python3 scripts/start_live_trading_robust.py
   ```

## Best Practices

1. ✅ **Backup regularly** - Daily or after significant data collection
2. ✅ **Test restores** - Verify backups work before you need them
3. ✅ **Multiple locations** - Store backups in different places
4. ✅ **Document backups** - Keep manifest files with metadata
5. ✅ **Automate** - Use cron jobs for scheduled backups
6. ✅ **Monitor size** - Track backup file sizes over time
7. ✅ **Rotate old backups** - Don't keep everything forever
8. ✅ **Secure backups** - Protect sensitive trading data

## Quick Commands

```bash
# Create backup
python3 scripts/backup_database_to_csv.py

# Restore backup
python3 scripts/restore_from_backup.py --file data/backups/all_data_backup_TIMESTAMP.csv

# List backups
ls -lh data/backups/

# Check backup size
du -sh data/backups/

# Compress old backups
gzip data/backups/*_backup_*.csv

# Copy to external drive
cp -r data/backups/ /media/external_drive/trading_backups/
```

## Summary

Your data is now safely backed up! You have:
- ✅ Complete backup of all 66,430 candles
- ✅ Individual symbol backups for selective restore
- ✅ Manifest file with metadata
- ✅ Restore scripts ready to use
- ✅ This guide for reference

Keep these backups safe and create new ones regularly as you collect more data!
