#!/bin/bash

# Template backup script for Multi-Model Prompt Engine

set -e

# Configuration
BACKUP_DIR="/backups/templates/$(date +%Y%m%d_%H%M%S)"
SOURCE_DIR="/app/templates"
LOG_FILE="/app/logs/backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Log backup start
echo "$(date): Starting template backup to $BACKUP_DIR" >> "$LOG_FILE"

# Copy templates
cp -r "$SOURCE_DIR" "$BACKUP_DIR"

# Create tar archive
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .

# Remove temporary directory
rm -rf "$BACKUP_DIR"

# Log backup completion
echo "$(date): Template backup completed: $BACKUP_DIR.tar.gz" >> "$LOG_FILE"

# Keep only last 10 backups
find /backups/templates -name "*.tar.gz" -type f -mtime +30 -delete

echo "Templates backed up to $BACKUP_DIR.tar.gz"
