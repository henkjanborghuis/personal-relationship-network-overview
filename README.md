# Personal Contacts Overview

A personal relationship management web app that uses **Apple Contacts** as its source of truth. It shows your contacts grouped by social circle, with multi-generational family trees, photos from Apple Photos, and a detail panel per person.

## Features

- Groups from Apple Contacts displayed as social circles
- Multi-generational family trees (couples + children, recursively)
- Photos synced from the Apple Photos People album
- Click-through detail panel (birthday, anniversary, family links, interests, notes)
- Zoom in/out on the family tree view (auto-fits to screen on open)
- Group selector dropdown in the main header — no need to use the sidebar
- Configurable default group (app opens directly in your most-used group)
- Egocentric focus navigator on mobile: tap any relative to re-center the view
- Dark mode (follows system preference, with manual toggle)
- Collapsible sidebar (collapsed by default on mobile/tablet)
- Accessible on your home network from any device
- Static HTML export for offline / on-the-go use (e.g. iCloud Drive)

---

## Requirements

- macOS (Apple Contacts + Apple Photos access required)
- Python 3.11+
- Node.js 18+

---

## First-time setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd fafo

# 2. Create your personal configuration file from the sample
cp backend/data/enrichment.yaml.sample backend/data/enrichment.yaml

# 3. Edit enrichment.yaml — at minimum, set sync_groups to your Apple Contacts group names
#    (or leave sync_groups empty to sync all contacts)

# 4. Start the app
./run.sh
```

This installs Python dependencies, builds the React frontend, and starts the server at **http://localhost:8000**.

On your home network, other devices can reach it at **http://\<your-mac-ip\>:8000**.

---

## Running

```bash
./run.sh              # normal start
./run.sh --rebuild    # force a frontend rebuild (after UI code changes)
```

On first launch the contacts list will be empty. Click **Sync Contacts** in the sidebar to import from Apple Contacts. macOS will prompt for Contacts access if not yet granted.

---

## Syncing contacts

Click **Sync Contacts** in the sidebar. The app will:

1. Export vCards from Apple Contacts (only the groups listed in `sync_groups`, see below)
2. Parse relationships (spouse, children, parents) from Related Names fields
3. Build family trees per group
4. Save contact photos to `backend/data/photos/`

Sync time depends on group size. With `sync_groups` configured it typically takes a few seconds.

---

## Syncing photos from Apple Photos

Photos are pulled from the **People album** in Apple Photos and set on matching Apple Contacts entries.

```bash
# Install dependencies (one-time)
pip3 install osxphotos pillow

# Preview which Photos persons match which contacts (dry run)
python3 sync_photos.py

# Apply — sets photos on matched contacts in Apple Contacts
python3 sync_photos.py --apply

# Apply using full key photo instead of face crop
python3 sync_photos.py --apply --no-crop

# Test with a single person (useful for debugging)
python3 sync_photos.py --apply --person "Jane Doe"

# Then sync in the app to pick up the updated photos
```

By default, photos are cropped to the detected face region (using Apple Photos face data) before being applied, so contact thumbnails show a tight portrait. Pass `--no-crop` to use the full key photo instead. If `pillow` is not installed, the script falls back to the full key photo automatically.

HEIC source photos are handled automatically via macOS `sips` (no extra dependencies). EXIF orientation is applied before cropping, so rotated originals come out correctly.

Matching is done by full name (case-insensitive). If a name in Apple Photos doesn't exactly match the name in Apple Contacts, it won't auto-match. Rename one side to fix it.

---

## Static HTML export

Generates a single self-contained HTML file that works without a running server.

```bash
python3 export.py

# Custom output path (e.g. iCloud Drive for on-the-go access)
python3 export.py --output ~/Library/Mobile\ Documents/com~apple~CloudDocs/contacts-overview.html

# Skip the Apple Contacts sync step (use cached data)
python3 export.py --skip-sync
```

The exported file embeds all contact data and the full UI. Open it in any browser.

---

## Configuration

All configuration lives in **`backend/data/enrichment.yaml`**.

> **Note:** `enrichment.yaml` is listed in `.gitignore` because it contains personal data (group names, contact UIDs, notes). A clean template is provided at `backend/data/enrichment.yaml.sample`. Copy it to `enrichment.yaml` to get started — it will never be committed to git.

### `default_group` — which group to open on startup

```yaml
default_group: "Familie Smit"
```

The app opens directly in this group instead of the "All contacts" view. Leave empty (or omit) to start with all contacts.

---

### `sync_groups` — which groups to sync

```yaml
sync_groups:
  - Bonteweg
  - Club Rijssen
  - Familie Borghuis
  - Familie Smit
  - Familie te Luggenhorst
  - Vrienden
```

Only contacts in these Apple Contacts groups are exported during sync. This keeps sync fast and focused. Set to `[]` (empty) to sync all groups — but this can be slow with many contacts.

---

### `families` — declare a family unit (fallback when Contacts has no relation data)

Declaring a family sets all parent→child links and marks all children as siblings. After that, **automatic inference** propagates those links further: siblings inherit shared parents, and contacts with shared parents are inferred as siblings. This runs every sync until no new links can be derived.

```yaml
families:
  Voortman:
    parents:
      - "UID-Johan-Voortman"
      - "UID-Alie-Voortman"
    children:
      - "UID-Rik-Voortman"
      - "UID-Geerd-Voortman"
      - "UID-Inge-Voortman"
      - "UID-Anne-Voortman"
```

Use this only for contacts with no Related Names set in Apple Contacts. If one sibling already has parents set in Contacts, inference will automatically propagate to the others — no `families:` entry needed.

---

### `relationships` — explicit family links

Use when Apple Contacts' Related Names fields can't be auto-resolved (e.g. ambiguous first names, or the relation isn't stored in Contacts).

```yaml
relationships:
  - from_uid: "3B3FF4E8-D7E4-4CE3-B39D-9D55E5B2C1A4"
    to_uid:   "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
    type: spouse    # spouse | child | parent | sibling

  - from_uid: "3B3FF4E8-D7E4-4CE3-B39D-9D55E5B2C1A4"
    to_uid:   "BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB"
    type: child
```

To find a contact's UID: open Apple Contacts → select the contact → Edit → scroll to the bottom. Or check `/api/diagnostics/unresolved` after a sync for a list of relationships that couldn't be resolved automatically.

---

### `groups` — supplement Apple Contacts groups

Assign contacts to additional groups without changing Apple Contacts.

```yaml
groups:
  My custom group:
    - "3B3FF4E8-D7E4-4CE3-B39D-9D55E5B2C1A4"
    - "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
```

---

### `contacts` — per-contact enrichment

Add interests and extra notes that aren't stored in Apple Contacts.

```yaml
contacts:
  "3B3FF4E8-D7E4-4CE3-B39D-9D55E5B2C1A4":
    interests:
      - cycling
      - photography
      - Italian cooking
    notes_extra: "Met at orientation week 2003. Prefers WhatsApp."
```

---

## API endpoints

The backend exposes a small REST API (useful for debugging):

| Endpoint | Description |
|---|---|
| `GET /api/sync` | Re-sync from Apple Contacts |
| `GET /api/groups` | List all groups with contact counts |
| `GET /api/groups/{name}` | Family tree view for a group |
| `GET /api/contacts` | All contacts (sorted by name) |
| `GET /api/contacts/{uid}` | Single contact by UID |
| `GET /api/settings` | App settings (e.g. `default_group`) |
| `GET /api/diagnostics/unresolved` | Relationships that couldn't be auto-resolved |
| `GET /api/docs` | Interactive API docs (Swagger UI) |

---

## Project structure

```
.
├── run.sh                  # Start the app
├── export.py               # Generate static HTML export
├── sync_photos.py          # Sync photos from Apple Photos → Apple Contacts
├── backend/
│   ├── main.py             # FastAPI app + API routes
│   ├── models.py           # Pydantic data models
│   ├── sync.py             # AppleScript export from Apple Contacts
│   ├── parser.py           # vCard parsing + relationship resolution
│   ├── grouper.py          # Family tree builder
│   ├── enrichment.py       # enrichment.yaml loader
│   ├── requirements.txt    # Python dependencies
│   └── data/
│       ├── enrichment.yaml.sample  # ← template — copy to enrichment.yaml
│       ├── enrichment.yaml         # your personal config (gitignored)
│       ├── contacts.vcf            # cached vCard export (gitignored, auto-generated)
│       ├── groups.json             # cached group data (gitignored, auto-generated)
│       └── photos/                 # contact photos (gitignored, auto-generated)
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   └── components/
    │       ├── GroupSidebar.jsx
    │       ├── FamilyTreePanel.jsx
    │       ├── FamilyTreeNode.jsx
    │       ├── FamilyNavigator.jsx
    │       ├── ContactDrawer.jsx
    │       ├── InitialsCircle.jsx
    │       ├── ZoomControls.jsx
    │       └── LandscapeGuard.jsx
    └── dist/               # built frontend (auto-generated)
```
