#!/bin/bash

# Template restore script for Multi-Model Prompt Engine

set -e

# Configuration
BACKUP_FILE="$1"
TARGET_DIR="/app/templates"
LOG_FILE="/app/logs/restore.log"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Log restore start
echo "$(date): Starting template restore from $BACKUP_FILE" >> "$LOG_FILE"

# Create backup of current templates
CURRENT_BACKUP="/app/templates_backup_$(date +%Y%m%d_%H%M%S)"
cp -r "$TARGET_DIR" "$CURRENT_BACKUP"

# Extract backup
tar -xzf "$BACKUP_FILE" -C "$TARGET_DIR"

# Log restore completion
echo "$(date): Template restore completed from $BACKUP_FILE" >> "$LOG_FILE"

echo "Templates restored from $BACKUP_FILE"
echo "Previous templates backed up to $CURRENT_BACKUP"
