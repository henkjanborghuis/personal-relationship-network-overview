"""
FastAPI backend for the personal contacts overview app.
"""
import logging
import subprocess
import uuid
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from enrichment import apply_enrichment, load_default_group, load_group_siblings
from grouper import build_group_view, build_all_group_views
from models import AppSettings, Contact, ExportResult, GroupSummary, GroupView, SyncResult, UnresolvedRelation
from parser import parse_contacts
from sync import sync_all

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Contacts Overview", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store — populated on startup and on /api/sync
_contacts: dict[str, Contact] = {}
_unresolved: list[dict] = []

# Short-lived export tokens: token → validated Path chosen by the server-side folder picker.
# Consumed on first use so each token is single-use.
_pending_exports: dict[str, Path] = {}

DATA_DIR = Path(__file__).parent / "data"
ENRICHMENT_FILE = DATA_DIR / "enrichment.yaml"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def _load_contacts() -> None:
    global _contacts, _unresolved
    vcf_path = DATA_DIR / "contacts.vcf"
    groups_path = DATA_DIR / "groups.json"

    if not vcf_path.exists():
        logger.warning("contacts.vcf not found — run /api/sync first")
        return

    import json
    groups_data: dict[str, list[str]] = {}
    if groups_path.exists():
        groups_data = json.loads(groups_path.read_text())

    all_names_path = DATA_DIR / "all_names.json"
    all_names = set(json.loads(all_names_path.read_text())) if all_names_path.exists() else None

    vcf_text = vcf_path.read_text(encoding="utf-8")
    _contacts, _unresolved = parse_contacts(vcf_text, groups_data, all_names)
    _contacts = apply_enrichment(_contacts, ENRICHMENT_FILE)
    logger.info(f"Loaded {len(_contacts)} contacts")


@app.on_event("startup")
def on_startup() -> None:
    _load_contacts()


@app.get("/api/sync", response_model=SyncResult)
def sync_contacts() -> SyncResult:
    """Re-export from Apple Contacts and reload data."""
    global _contacts, _unresolved
    import json

    vcf_text, groups_data, all_names = sync_all()
    # Persist groups for future loads
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "groups.json").write_text(
        json.dumps(groups_data, ensure_ascii=False), encoding="utf-8"
    )

    _contacts, _unresolved = parse_contacts(vcf_text, groups_data, all_names)
    _contacts = apply_enrichment(_contacts, ENRICHMENT_FILE)

    return SyncResult(
        contacts_count=len(_contacts),
        groups_count=len(groups_data),
        unresolved_count=len(_unresolved),
    )


@app.get("/api/groups", response_model=list[GroupSummary])
def get_groups() -> list[GroupSummary]:
    all_groups: dict[str, int] = {}
    for c in _contacts.values():
        for g in c.groups:
            all_groups[g] = all_groups.get(g, 0) + 1
    return [GroupSummary(name=name, count=count) for name, count in sorted(all_groups.items())]


@app.get("/api/groups/{group_name}", response_model=GroupView)
def get_group_view(group_name: str) -> GroupView:
    group_name = unquote(group_name)
    group_contacts = {uid: c for uid, c in _contacts.items() if group_name in c.groups}
    if not group_contacts:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found or empty")
    group_siblings = load_group_siblings(ENRICHMENT_FILE)
    return build_group_view(group_name, group_contacts, group_siblings=group_siblings)


@app.get("/api/contacts", response_model=list[Contact])
def get_all_contacts() -> list[Contact]:
    return sorted(_contacts.values(), key=lambda c: (c.last_name.lower(), c.first_name.lower()))


@app.get("/api/contacts/{uid}", response_model=Contact)
def get_contact(uid: str) -> Contact:
    if uid not in _contacts:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _contacts[uid]


@app.get("/api/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    """Returns app settings (e.g. default_group) from enrichment.yaml."""
    return AppSettings(default_group=load_default_group(ENRICHMENT_FILE))


@app.get("/api/diagnostics/unresolved", response_model=list[UnresolvedRelation])
def get_unresolved() -> list[UnresolvedRelation]:
    """Returns relationships that couldn't be auto-resolved (add to enrichment.yaml)."""
    return [UnresolvedRelation(**r) for r in _unresolved]


def _allowed_export_dirs() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "Library" / "Mobile Documents" / "com~apple~CloudDocs",
    ]
    return [p for p in candidates if p.exists()]


def _run_export(output_dir: Path) -> ExportResult:
    """Build and write the HTML export to a fully server-controlled Path."""
    from exporter import build_app_data, embed_photos, build_frontend, inline_assets

    output_path = output_dir / "contacts-overview.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    app_data = build_app_data(_contacts, ENRICHMENT_FILE)
    embed_photos(app_data["contacts"], DATA_DIR / "photos")

    dist = build_frontend(FRONTEND_DIR)
    html = inline_assets(dist, app_data)
    output_path.write_text(html, encoding="utf-8")

    return ExportResult(
        output_path=str(output_path),
        size_kb=output_path.stat().st_size // 1024,
        contacts_count=len(_contacts),
        groups_count=len(app_data["groups"]),
    )


@app.get("/api/export/destinations")
def get_export_destinations() -> dict:
    """Return which export destinations are available on this machine."""
    home = Path.home()
    downloads = home / "Downloads"
    icloud = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    return {
        "downloads": downloads.exists(),
        "icloud": icloud.exists(),
    }


@app.get("/api/export/pick-directory")
def pick_directory() -> dict:
    """
    Show the native macOS folder picker (opening inside iCloud Drive).
    Validates the chosen path against the allowlist, stores it server-side,
    and returns a single-use token. The path never travels back over HTTP.
    """
    icloud = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    default = str(icloud) if icloud.exists() else str(Path.home())
    result = subprocess.run(
        ["osascript", "-e",
         f'POSIX path of (choose folder with prompt "Select folder in iCloud Drive"'
         f' default location POSIX file "{default}")'],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"token": None}  # user cancelled

    chosen = Path(result.stdout.strip()).resolve()
    allowed = [p.resolve() for p in _allowed_export_dirs()]
    if not any(chosen == a or chosen.is_relative_to(a) for a in allowed):
        raise HTTPException(status_code=400, detail="Chosen folder is outside allowed locations")

    token = str(uuid.uuid4())
    _pending_exports[token] = chosen
    return {"token": token}


@app.get("/api/export/to-downloads", response_model=ExportResult)
def export_to_downloads() -> ExportResult:
    """Export directly to ~/Downloads — no user-supplied path."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        raise HTTPException(status_code=400, detail="Downloads folder not found")
    return _run_export(downloads)


@app.get("/api/export", response_model=ExportResult)
def export_html(token: str) -> ExportResult:
    """
    Run the export using a path stored server-side by pick_directory.
    Consumes the token on first use.
    """
    output_dir = _pending_exports.pop(token, None)
    if output_dir is None:
        raise HTTPException(status_code=400, detail="Invalid or expired export token")
    return _run_export(output_dir)


# Serve contact photos
PHOTOS_DIR = DATA_DIR / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")

# Serve built frontend — must be last so API routes take precedence
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")
