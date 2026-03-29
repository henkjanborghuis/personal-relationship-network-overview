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
import base64
import json
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
OUTPUT_DEFAULT = ROOT / "output" / "contacts-overview.html"


def build_app_data(contacts: dict, groups_data: dict) -> dict:
    """Build the full data payload that will be embedded in the HTML."""
    from grouper import build_all_group_views

    group_views = build_all_group_views(contacts)

    all_group_names: set[str] = set()
    for c in contacts.values():
        all_group_names.update(c.groups)

    groups_list = sorted(
        [
            {
                "name": name,
                "count": sum(1 for c in contacts.values() if name in c.groups),
            }
            for name in all_group_names
        ],
        key=lambda g: g["name"],
    )

    return {
        "contacts": {uid: c.dict() for uid, c in contacts.items()},
        "groups": groups_list,
        "groupViews": {name: view.dict() for name, view in group_views.items()},
    }


PHOTO_THUMBNAIL_PX = 120


def embed_photos(contacts_data: dict, photos_dir: Path) -> None:
    """
    Replace photo_url path strings with base64 data URLs (resized thumbnails).
    Mutates contacts_data in place.  Uses macOS sips — no extra dependencies.
    """
    with_photos = [uid for uid, c in contacts_data.items() if c.get("photo_url")]
    if not with_photos:
        return

    logger.info(f"Embedding {len(with_photos)} contact photos as thumbnails…")
    embedded = 0
    for uid in with_photos:
        photo_path = photos_dir / f"{uid}.jpg"
        if not photo_path.exists():
            continue
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            subprocess.run(
                [
                    "sips",
                    "--resampleHeightWidthMax", str(PHOTO_THUMBNAIL_PX),
                    str(photo_path),
                    "--out", str(tmp_path),
                ],
                capture_output=True,
                check=True,
            )
            b64 = base64.b64encode(tmp_path.read_bytes()).decode("ascii")
            tmp_path.unlink(missing_ok=True)
            contacts_data[uid]["photo_url"] = f"data:image/jpeg;base64,{b64}"
            embedded += 1
        except Exception as exc:
            logger.warning(f"Could not embed photo for {uid}: {exc}")

    logger.info(f"Embedded {embedded}/{len(with_photos)} photos")


def build_frontend() -> Path:
    logger.info("Building frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("Frontend build failed")
    dist = FRONTEND / "dist"
    logger.info(f"Frontend built → {dist}")
    return dist


def inline_assets(dist: Path, app_data: dict) -> str:
    """
    Inline all JS and CSS into index.html and inject the contact data.
    Produces a single self-contained HTML file.
    """
    html = (dist / "index.html").read_text(encoding="utf-8")

    # Inline CSS <link rel="stylesheet" href="...">
    def replace_link(m):
        href = m.group(1).lstrip("/")
        css_path = dist / href
        if css_path.exists():
            css = css_path.read_text(encoding="utf-8")
            return f"<style>{css}</style>"
        return m.group(0)

    html = re.sub(
        r'<link[^>]+rel="stylesheet"[^>]+href="(/[^"]+)"[^>]*/?>',
        replace_link,
        html,
    )

    # Inline <script type="module" ... src="...">
    def replace_script(m):
        src = m.group(1).lstrip("/")
        js_path = dist / src
        if js_path.exists():
            js = js_path.read_text(encoding="utf-8")
            return f"<script type=\"module\">{js}</script>"
        return m.group(0)

    html = re.sub(
        r'<script\b[^>]*\bsrc="(/[^"]+)"[^>]*></script>',
        replace_script,
        html,
    )

    # Inject contact data before </head>
    data_json = json.dumps(app_data, ensure_ascii=False, default=str)
    data_script = f"<script>window.__APP_DATA__={data_json};</script>"
    html = html.replace("</head>", data_script + "\n</head>", 1)

    return html


def main():
    parser = argparse.ArgumentParser(description="Export contacts overview as a single HTML file")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT, help="Output path")
    parser.add_argument("--skip-sync", action="store_true", help="Use cached contacts.vcf instead of re-syncing")
    args = parser.parse_args()

    sys.path.insert(0, str(BACKEND))

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
        vcf_text, groups_data = sync_all()
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

    app_data = build_app_data(contacts, groups_data)
    embed_photos(app_data["contacts"], BACKEND / "data" / "photos")

    dist = build_frontend()
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
