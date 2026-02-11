#!/usr/bin/env bash
# Small helper script to create a MySQL dump. Configure environment variables in your host:
# MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
# Example usage (PythonAnywhere):
# ~/envs/mimenudigital/bin/python -c "import os; print(os.getenv('MYSQL_HOST'))"

set -euo pipefail
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-$HOME/db_backups}"
mkdir -p "$BACKUP_DIR"
DUMP_FILE="$BACKUP_DIR/menu_digital_$TIMESTAMP.sql.gz"

# Use mysqldump if available
if ! command -v mysqldump >/dev/null 2>&1; then
  echo "mysqldump not found in PATH. Install MySQL client tools or run this from a host with mysqldump."
  exit 1
fi

# Read credentials from environment (do not hardcode)
: "${MYSQL_HOST:?Need MYSQL_HOST env var}"
: "${MYSQL_USER:?Need MYSQL_USER env var}"
: "${MYSQL_DB:?Need MYSQL_DB env var}"

# WARNING: Using MYSQL_PWD environment variable avoids prompting; ensure file permissions are correct
export MYSQL_PWD="${MYSQL_PASSWORD:-}"

echo "Creating DB dump to $DUMP_FILE"
mysqldump -h "$MYSQL_HOST" -u "$MYSQL_USER" "$MYSQL_DB" | gzip > "$DUMP_FILE"
if [ $? -eq 0 ]; then
  echo "Backup saved to $DUMP_FILE"
else
  echo "Backup failed"
  exit 1
fi

# Optional: upload to S3 if AWS env vars present
if [ -n "${AWS_S3_BUCKET:-}" ]; then
  if command -v aws >/dev/null 2>&1; then
    aws s3 cp "$DUMP_FILE" "s3://$AWS_S3_BUCKET/$(basename "$DUMP_FILE")"
    echo "Uploaded backup to s3://$AWS_S3_BUCKET/"
  else
    echo "AWS CLI not found; skipping S3 upload"
  fi
fi
