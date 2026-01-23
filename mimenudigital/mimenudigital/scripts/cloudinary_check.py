#!/usr/bin/env python3
"""scripts/cloudinary_check.py
Simple helper to verify Cloudinary configuration and perform a test upload.
Usage:
  python scripts/cloudinary_check.py --url <image_url>
  python scripts/cloudinary_check.py --file <path_to_file>

Exit code 0 on success (prints JSON result), non-zero on error.
"""
import os
import sys
import argparse
import json

try:
    import cloudinary
    from cloudinary.uploader import upload as cloudinary_upload
except Exception as e:
    print(json.dumps({"ok": False, "error": "cloudinary SDK not installed: pip install cloudinary", "detail": str(e)}))
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description="Cloudinary check and test upload")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', help='Public image URL to fetch and upload to Cloudinary')
    group.add_argument('--file', help='Local image file to upload')
    args = parser.parse_args()

    cloudinary_url = os.environ.get('CLOUDINARY_URL')
    if not cloudinary_url:
        print(json.dumps({"ok": False, "error": "CLOUDINARY_URL not set in environment"}))
        sys.exit(3)

    try:
        # Initialize configuration from CLOUDINARY_URL
        cloudinary.config_from_url(cloudinary_url)
    except Exception as e:
        print(json.dumps({"ok": False, "error": "Failed to configure cloudinary from CLOUDINARY_URL", "detail": str(e)}))
        sys.exit(4)

    try:
        if args.url:
            result = cloudinary_upload(args.url, folder='mimenudigital/test', resource_type='image')
        else:
            # args.file
            if not os.path.exists(args.file):
                print(json.dumps({"ok": False, "error": f"File not found: {args.file}"}))
                sys.exit(5)
            result = cloudinary_upload(args.file, folder='mimenudigital/test', resource_type='image')

        # Print useful info
        out = {
            'ok': True,
            'public_id': result.get('public_id'),
            'url': result.get('secure_url') or result.get('url'),
            'raw': result
        }
        print(json.dumps(out))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({"ok": False, "error": "Upload failed", "detail": str(e)}))
        sys.exit(6)


if __name__ == '__main__':
    main()
