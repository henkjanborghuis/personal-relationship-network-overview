# Claude instructions for this project

This file contains guidance for working on this codebase. Follow these rules on every task.

---

## Keep README.md in sync

Update `README.md` whenever you make a structural change:
- New script or file added to the project root or backend
- New API endpoint added to `main.py`
- New configuration key added to `enrichment.yaml`
- New component added to `frontend/src/components/`
- Changes to how `run.sh`, `export.py`, or `sync_photos.py` are used

Do not document minor internal refactors.

---

## Architecture

Full-stack local app. Python backend, React frontend, Apple Contacts as data source.

```
run.sh → uvicorn backend/main.py → FastAPI
                                 → /api/* endpoints
                                 → /photos/* static files (contact photos)
                                 → /* frontend/dist (built React app)

Apple Contacts (AppleScript) → sync.py → parser.py → grouper.py → API responses
enrichment.yaml              → enrichment.py ↗

export.py → syncs contacts + builds frontend → inlines into single HTML file
sync_photos.py → osxphotos + AppleScript → sets photos in Apple Contacts
```

---

## Key technical decisions

### Contact identity: X-ABUID, not UID
Apple Contacts vCards contain two different ID fields:
- `X-ABUID:` — the internal Contacts.app identifier, matches AppleScript `id of p`. **Use this one.**
- `UID:` — the vCard interchange ID. Different value. Do not use for matching.

`parser.py` prefers `X-ABUID` via `_contents_lower()` + `contents.get("x-abuid", [])`.
`_normalize_uid()` strips the `:ABPerson` suffix Apple appends.

### Family relationship labels
Apple stores relationship labels as `_$!<Mother>!$_`, `_$!<Spouse>!$_`, etc.
`_parse_label()` in `parser.py` normalises these to lowercase: `"mother"`, `"spouse"`.
`_apply_relation()` handles: `spouse/partner/husband/wife`, `child/son/daughter`, `parent/mother/father`, `sibling/brother/sister`.

### Family tree model
`FamilyNode` in `models.py` is a recursive Pydantic model:
```python
class FamilyNode(BaseModel):
    couple: list[str]          # 1 or 2 UIDs
    children: list[FamilyNode] # each child's own subtree
```
`grouper.py` builds trees from roots down. Roots = contacts with no parents in the group AND not a spouse of someone who is a child-in-group. Co-parents (sharing a child but no explicit spouse link) are detected in a second pass.

### Dark mode
Uses Tailwind `darkMode: 'class'`. The `<html>` element gets the `dark` class toggled via `document.documentElement.classList.toggle('dark', isDark)` in `App.jsx`. Do not use `darkMode: 'media'`.

### Photo serving
Photos are written to `backend/data/photos/{uid}.jpg` during sync (by `parser.py`).
Served as static files at `/photos/{uid}.jpg` via a FastAPI `StaticFiles` mount in `main.py`.
The Vite dev server proxies `/photos` to `http://localhost:8000` (configured in `vite.config.js`).
`Contact.photo_url` holds the path string (e.g. `"/photos/ABC123.jpg"`) or `None`.
Do NOT embed photos as base64 data URLs — contact photos can be 5–7 MB each.

### Static export
`export.py` builds the frontend, then inlines `assets/main.js` and `assets/main.css` into a single HTML file and injects `window.__APP_DATA__ = {...}` before `</head>`.
`api.js` checks `window.__APP_DATA__` at runtime and uses it instead of fetching if present.
Photos are NOT included in the static export (they'd make the file enormous).

### Sync filtering
`sync.py` reads `sync_groups` from `enrichment.yaml` before running AppleScript.
If the list is non-empty, AppleScript only iterates members of those groups — much faster than iterating all contacts. Duplicate contacts (in multiple groups) are deduplicated by UID within the AppleScript using a `seen` list.

---

## Data flow on sync

1. `sync.py` reads `sync_groups` from `enrichment.yaml`
2. AppleScript exports vCards for those groups → `data/contacts.vcf`
3. AppleScript exports group membership → `data/groups.json`
4. `parser.py` parses vCards → `dict[uid, Contact]`, writes `data/photos/{uid}.jpg`
5. `enrichment.py` merges `enrichment.yaml` (relationships, extra groups, interests, notes)
6. `grouper.py` builds `GroupView` (trees + singles) per group on demand

---

## Running locally for development

```bash
# Terminal 1 — backend with hot reload
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — frontend dev server (proxies /api and /photos to :8000)
npm --prefix frontend run dev
# → http://localhost:5173
```

Or use `.claude/launch.json` configurations.

---

## Verification after UI changes

After editing any `.jsx` or `.css` file while the Vite dev server is running:
- Vite hot-reloads automatically — no action needed for most changes
- If Tailwind classes were added that weren't in the build before, a full page reload may be needed
- Use the preview screenshot tool to verify visual changes before finishing

After editing backend Python files while uvicorn is running with `--reload`:
- uvicorn reloads automatically
- If `enrichment.yaml` was changed, click **Sync Contacts** in the app to reload data

---

## Adding a new enrichment.yaml key

1. Add the key to `backend/data/enrichment.yaml` (with comments and example)
2. Read it in `enrichment.py`
3. Update the **Configuration** section in `README.md`

## Adding a new API endpoint

1. Add the route to `backend/main.py`
2. Add a Pydantic response model to `backend/models.py` if needed
3. Update the **API endpoints** table in `README.md`

## Adding a new frontend component

1. Create `frontend/src/components/ComponentName.jsx`
2. Update the **Project structure** section in `README.md`

---

## Things to avoid

- Never use `UID:` vCard field as a contact identifier (use `X-ABUID:`)
- Never embed photos as base64 in API responses or Contact models
- Never use `darkMode: 'media'` in `tailwind.config.js`
- Never use the AppleScript variable name `result` (reserved word — causes `-10006` errors)
- Never skip calling `FamilyNode.model_rebuild()` after the class definition
- Don't run `git add -A` or commit unless the user explicitly asks
