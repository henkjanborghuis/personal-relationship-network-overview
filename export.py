#!/usr/bin/env python3
"""
Generates a self-contained single-file HTML export of your contacts overview.
The output file can be opened in any browser — no server needed.
Put it in iCloud Drive to access it anywhere.

Usage:
    python3 export.py
    python3 export.py --output ~/iCloud\ Drive/contacts-overview.html
"""
import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
OUTPUT_DEFAULT = ROOT / "output" / "contacts-overview.html"

sys.path.insert(0, str(BACKEND))
from exporter import build_app_data, embed_photos, build_frontend, inline_assets  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Export contacts overview as a single HTML file")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT, help="Output path")
    parser.add_argument("--skip-sync", action="store_true", help="Use cached contacts.vcf instead of re-syncing")
    args = parser.parse_args()

    from enrichment import apply_enrichment
    from parser import parse_contacts

    if args.skip_sync:
        logger.info("Using cached contacts (--skip-sync)")
        vcf_path = BACKEND / "data" / "contacts.vcf"
        groups_path = BACKEND / "data" / "groups.json"
        if not vcf_path.exists():
            print("ERROR: No cached contacts found. Run without --skip-sync first.")
            sys.exit(1)
        vcf_text = vcf_path.read_text(encoding="utf-8")
        groups_data = json.loads(groups_path.read_text()) if groups_path.exists() else {}
    else:
        from sync import sync_all
        logger.info("Syncing from Apple Contacts...")
        vcf_text, groups_data, _ = sync_all()
        # Persist for future --skip-sync runs
        groups_path = BACKEND / "data" / "groups.json"
        groups_path.parent.mkdir(exist_ok=True)
        groups_path.write_text(json.dumps(groups_data, ensure_ascii=False), encoding="utf-8")

    contacts, unresolved = parse_contacts(vcf_text, groups_data)
    contacts = apply_enrichment(contacts, BACKEND / "data" / "enrichment.yaml")

    if unresolved:
        logger.warning(
            f"{len(unresolved)} relationships could not be auto-resolved. "
            "Run the local server and visit /api/diagnostics/unresolved for details."
        )

    app_data = build_app_data(contacts, BACKEND / "data" / "enrichment.yaml")
    embed_photos(app_data["contacts"], BACKEND / "data" / "photos")

    dist = build_frontend(FRONTEND)
    html = inline_assets(dist, app_data)

    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    size_kb = output.stat().st_size // 1024
    print(f"\nExport complete!")
    print(f"  File : {output}")
    print(f"  Size : {size_kb} KB")
    print(f"  People: {len(contacts)}")
    print(f"  Groups: {len(app_data['groups'])}")
    print(f"\nOpen the file in any browser, or copy it to iCloud Drive.")


if __name__ == "__main__":
    main()
