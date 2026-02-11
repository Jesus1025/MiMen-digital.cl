#!/usr/bin/env python3
"""
Worker script to process records in `imagenes_pendientes`.
Usage:
    python scripts/process_pending_images.py [--limit N] [--max-attempts M] [--dry-run]

It will attempt to upload local files to Cloudinary and update the record, set status to 'uploaded' on success
or increment attempts and set status to 'failed' after max attempts. It logs progress and returns non-zero
code on unrecoverable errors.
"""
import os
import sys
import argparse
import logging
import time

from pathlib import Path

# Make sure we can import app context
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import app_menu as app_menu_mod

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('process_pending_images')

DEFAULT_MAX_ATTEMPTS = 5


def process(limit=50, max_attempts=DEFAULT_MAX_ATTEMPTS, dry_run=False):
    # Attempt to initialize Cloudinary at runtime to be test-friendly
    try:
        app_menu_mod.init_cloudinary()
    except Exception as e:
        logger.debug('init_cloudinary failed: %s', e)

    if not app_menu_mod.CLOUDINARY_AVAILABLE or not app_menu_mod.CLOUDINARY_CONFIGURED:
        logger.error('Cloudinary not available or not configured. Aborting.')
        return 2

    db = app_menu_mod.get_db()
    processed = 0

    try:
        with db.cursor() as cur:
            cur.execute("SELECT id, restaurante_id, plato_id, local_path, source_url, attempts, status FROM imagenes_pendientes WHERE status = 'pending' ORDER BY created_at ASC LIMIT %s", (limit,))
            rows = cur.fetchall()

            for row in rows:
                pid = row['id']
                restaurante_id = row['restaurante_id']
                local_path = row['local_path']
                attempts = row.get('attempts', 0) or 0

                logger.info('Processing pending id=%s attempts=%s local_path=%s', pid, attempts, local_path)

                if not os.path.exists(local_path):
                    logger.warning('Local path missing for pending id=%s. Marking as failed.', pid)
                    cur.execute("UPDATE imagenes_pendientes SET status=%s, last_error=%s, attempts=%s, updated_at=NOW() WHERE id=%s", ('failed', 'local_file_missing', attempts + 1, pid))
                    db.commit()
                    processed += 1
                    continue

                if attempts >= max_attempts:
                    logger.warning('Max attempts reached for pending id=%s. Marking as failed.', pid)
                    cur.execute("UPDATE imagenes_pendientes SET status=%s, last_error=%s, attempts=%s, updated_at=NOW() WHERE id=%s", ('failed', 'max_attempts_exceeded', attempts, pid))
                    db.commit()
                    processed += 1
                    continue

                if dry_run:
                    logger.info('Dry-run: would attempt upload for pending id=%s', pid)
                    continue

                try:
                    with open(local_path, 'rb') as fh:
                        result = app_menu_mod.cloudinary_upload(fh, folder=f"mimenudigital/platos/{restaurante_id}", quality='auto', fetch_format='auto', resource_type='auto')

                    public_id = result.get('public_id')
                    secure_url = result.get('secure_url')

                    if not public_id or not secure_url:
                        raise Exception('Cloudinary did not return public_id or secure_url')

                    # Update imagenes_pendientes
                    cur.execute("UPDATE imagenes_pendientes SET status=%s, attempts=%s, public_id=%s, url=%s, updated_at=NOW() WHERE id=%s", ('uploaded', attempts + 1, public_id, secure_url, pid))

                    # If it has a plato_id, update platos table imagen_public_id and imagen_url
                    cur.execute("SELECT plato_id FROM imagenes_pendientes WHERE id=%s", (pid,))
                    res = cur.fetchone()
                    plato_id = res.get('plato_id') if res else None
                    if plato_id:
                        cur.execute("UPDATE platos SET imagen_public_id=%s, imagen_url=%s WHERE id=%s", (public_id, secure_url, plato_id))

                    db.commit()
                    logger.info('Uploaded pending id=%s -> public_id=%s', pid, public_id)
                    processed += 1

                except Exception as e:
                    logger.exception('Error processing pending id=%s: %s', pid, e)
                    cur.execute("UPDATE imagenes_pendientes SET attempts=%s, last_error=%s, updated_at=NOW() WHERE id=%s", (attempts + 1, str(e), pid))
                    db.commit()
                    processed += 1

    except Exception as ex:
        logger.exception('Fatal error during processing: %s', ex)
        return 1

    logger.info('Processing complete, processed=%s', processed)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process pending Cloudinary uploads')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--max-attempts', type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    sys.exit(process(limit=args.limit, max_attempts=args.max_attempts, dry_run=args.dry_run))