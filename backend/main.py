"""
FastAPI backend for the personal contacts overview app.
"""
import logging
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from enrichment import apply_enrichment, load_default_group
from grouper import build_group_view, build_all_group_views
from models import AppSettings, Contact, GroupSummary, GroupView, SyncResult, UnresolvedRelation
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

DATA_DIR = Path(__file__).parent / "data"
ENRICHMENT_FILE = DATA_DIR / "enrichment.yaml"


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

    vcf_text = vcf_path.read_text(encoding="utf-8")
    _contacts, _unresolved = parse_contacts(vcf_text, groups_data)
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

    vcf_text, groups_data = sync_all()
    # Persist groups for future loads
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "groups.json").write_text(
        json.dumps(groups_data, ensure_ascii=False), encoding="utf-8"
    )

    _contacts, _unresolved = parse_contacts(vcf_text, groups_data)
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
    return build_group_view(group_name, group_contacts)


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


# Serve contact photos
PHOTOS_DIR = DATA_DIR / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")

# Serve built frontend — must be last so API routes take precedence
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")
