"""
Core export helpers shared by export.py (CLI) and main.py (API endpoint).
"""
import base64
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

PHOTO_THUMBNAIL_PX = 120


def build_app_data(contacts: dict, enrichment_path: Path) -> dict:
    """Build the full data payload that will be embedded in the HTML."""
    from grouper import build_all_group_views
    from enrichment import load_default_group

    group_views = build_all_group_views(contacts)
    default_group = load_default_group(enrichment_path)

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
        "contacts": {uid: c.model_dump() for uid, c in contacts.items()},
        "groups": groups_list,
        "groupViews": {name: view.model_dump() for name, view in group_views.items()},
        "settings": {"default_group": default_group},
    }


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
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
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
            contacts_data[uid]["photo_url"] = f"data:image/jpeg;base64,{b64}"
            embedded += 1
        except Exception as exc:
            logger.warning(f"Could not embed photo for {uid}: {exc}")
        finally:
            tmp_path.unlink(missing_ok=True)

    logger.info(f"Embedded {embedded}/{len(with_photos)} photos")


def build_frontend(frontend_dir: Path) -> Path:
    logger.info("Building frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Frontend build failed:\n{result.stderr}")
    dist = frontend_dir / "dist"
    logger.info(f"Frontend built → {dist}")
    return dist


def inline_assets(dist: Path, app_data: dict) -> str:
    """
    Inline all JS and CSS into index.html and inject the contact data.
    Produces a single self-contained HTML file.
    """
    html = (dist / "index.html").read_text(encoding="utf-8")

    # Inline favicon as base64 data URL so file:// opens don't 404
    favicon_path = dist / "favicon.svg"
    if favicon_path.exists():
        b64 = base64.b64encode(favicon_path.read_bytes()).decode("ascii")
        html = html.replace(
            'href="/favicon.svg"',
            f'href="data:image/svg+xml;base64,{b64}"',
        )

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

    # Collect JS from <script src="..."> tags and remove them from <head>.
    # We inject them before </body> instead so the DOM is ready when they run.
    collected_scripts: list[str] = []

    def replace_script(m):
        src = m.group(1).lstrip("/")
        js_path = dist / src
        if js_path.exists():
            collected_scripts.append(js_path.read_text(encoding="utf-8"))
            return ""  # remove from <head>
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

    # Inject app scripts before </body> — DOM is fully parsed at this point
    for js in collected_scripts:
        html = html.replace("</body>", f"<script>{js}</script>\n</body>", 1)

    return html
