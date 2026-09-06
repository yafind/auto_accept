#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BACKUP_DIR="$ROOT/backups"
mkdir -p "$BACKUP_DIR"
cp "$ROOT/${DATABASE_PATH:-bot.db}" "$BACKUP_DIR/bot-$(date +%Y-%m-%d).db"
find "$BACKUP_DIR" -type f -name 'bot-*.db' -mtime +7 -delete
