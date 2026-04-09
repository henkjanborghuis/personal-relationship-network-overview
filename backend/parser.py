"""
Parses Apple Contacts vCards into Contact objects and resolves relationships.
"""
import re
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import vobject

from models import Contact, RawRelation

logger = logging.getLogger(__name__)

APPLE_LABEL_RE = re.compile(r"_\$!<(.+?)>!\$_")


def _parse_label(raw: str) -> str:
    """Normalize Apple label format '_$!<Spouse>!$_' → 'spouse'."""
    m = APPLE_LABEL_RE.match(raw.strip())
    return m.group(1).lower() if m else raw.lower().strip()


def _normalize_uid(uid: str) -> str:
    """Strip ':ABPerson' suffix Apple appends to UIDs."""
    return uid.split(":")[0] if ":" in uid else uid


def _parse_date(value) -> Optional[str]:
    """Convert various date formats to ISO string (YYYY-MM-DD or --MM-DD for no-year)."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if not s:
        return None
    # No-year format: --MM-DD or --MMDD
    if s.startswith("--"):
        return s if len(s) == 7 else None  # Keep --MM-DD as-is for display
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def _get_initials(first: str, last: str) -> str:
    parts = [n[0].upper() for n in [first, last] if n]
    return "".join(parts) or "?"


def _contents_lower(vcard) -> dict:
    """Return vcard.contents with all keys lowercased."""
    result: dict[str, list] = {}
    for key, props in vcard.contents.items():
        result.setdefault(key.lower(), []).extend(props)
    return result


def _parse_vcard(vcard) -> Optional[Contact]:
    try:
        contents = _contents_lower(vcard)

        # Prefer X-ABUID (the Contacts.app internal ID, matches AppleScript `id of p`)
        # over UID (the vCard interchange ID, which is different)
        x_abuid_props = contents.get("x-abuid", [])
        uid_props = contents.get("uid", [])
        raw_uid = (
            x_abuid_props[0].value.strip() if x_abuid_props
            else uid_props[0].value.strip() if uid_props
            else None
        )
        if not raw_uid:
            return None
        uid = _normalize_uid(raw_uid)
        if not uid:
            return None

        fn_props = contents.get("fn", [])
        display_name = fn_props[0].value.strip() if fn_props else ""

        first_name = last_name = ""
        n_props = contents.get("n", [])
        if n_props:
            n = n_props[0].value
            first_name = (getattr(n, "given", "") or "").strip()
            last_name = (getattr(n, "family", "") or "").strip()
        if not display_name:
            display_name = f"{first_name} {last_name}".strip()
        if not first_name and not last_name and display_name:
            parts = display_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        phones = list({p.value.strip() for p in contents.get("tel", []) if p.value.strip()})
        emails = list({p.value.strip() for p in contents.get("email", []) if p.value.strip()})

        birthday = None
        for p in contents.get("bday", []):
            birthday = _parse_date(p.value)
            break

        nickname = None
        for p in contents.get("nickname", []):
            v = p.value.strip()
            if v:
                nickname = v
                break

        notes = None
        for p in contents.get("note", []):
            v = p.value.strip()
            if v:
                notes = v
                break

        photo_bytes = None
        for p in contents.get("photo", []):
            try:
                raw = p.value
                if isinstance(raw, bytes) and raw:
                    photo_bytes = raw
            except Exception:
                pass
            break

        # Collect itemized Apple properties grouped by item prefix (item1, item2, ...)
        item_groups: dict[str, dict] = {}
        for key, props in contents.items():
            for prop in props:
                grp = getattr(prop, "group", None)
                if grp:
                    item_groups.setdefault(grp, {})[key] = prop.value

        anniversary = None
        raw_related: list[RawRelation] = []

        death_date = None
        for item_data in item_groups.values():
            label_raw = item_data.get("x-ablabel", "")
            label = _parse_label(label_raw)

            if "x-abdate" in item_data and label == "anniversary":
                anniversary = _parse_date(item_data["x-abdate"])

            if "x-abdate" in item_data and label == "sterfdag":
                death_date = _parse_date(item_data["x-abdate"])

            if "x-abrelatednames" in item_data:
                name = item_data["x-abrelatednames"].strip()
                if name:
                    raw_related.append(RawRelation(name=name, label=label))

        contact = Contact(
            uid=uid,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            nickname=nickname,
            initials=_get_initials(first_name, last_name),
            phone_numbers=phones,
            emails=emails,
            birthday=birthday,
            anniversary=anniversary,
            death_date=death_date,
            notes=notes,
            raw_related=raw_related,
        )
        return contact, photo_bytes
    except Exception as e:
        logger.debug(f"Skipped vCard: {e}")
        return None, None


def _apply_relation(contacts: dict[str, Contact], from_uid: str, to_uid: str, label: str) -> None:
    src = contacts[from_uid]
    tgt = contacts[to_uid]

    if label in ("spouse", "partner", "husband", "wife"):
        if not src.spouse_uid:
            src.spouse_uid = to_uid
        if not tgt.spouse_uid:
            tgt.spouse_uid = from_uid
    elif label in ("child", "son", "daughter"):
        if to_uid not in src.children_uids:
            src.children_uids.append(to_uid)
        if from_uid not in tgt.parent_uids:
            tgt.parent_uids.append(from_uid)
    elif label in ("parent", "mother", "father"):
        if to_uid not in src.parent_uids:
            src.parent_uids.append(to_uid)
        if from_uid not in tgt.children_uids:
            tgt.children_uids.append(from_uid)
    elif label in ("sibling", "brother", "sister"):
        if to_uid not in src.sibling_uids:
            src.sibling_uids.append(to_uid)
        if from_uid not in tgt.sibling_uids:
            tgt.sibling_uids.append(from_uid)


def _resolve_relationships(
    contacts: dict[str, Contact],
    all_contact_names: set[str] | None = None,
) -> list[dict]:
    """
    Attempt to resolve raw Related Names text → contact UIDs.
    Returns list of unresolved / ambiguous relations for diagnostics.

    Resolution order:
    1. Nickname (exact match wins if unique)
    2. Full display name
    3. First name only (fallback hint)
    """
    # Build case-insensitive name → UIDs indices
    by_nickname: dict[str, list[str]] = {}
    by_full: dict[str, list[str]] = {}
    by_first: dict[str, list[str]] = {}
    for uid, c in contacts.items():
        if c.nickname:
            by_nickname.setdefault(c.nickname.lower().strip(), []).append(uid)
        full = c.display_name.lower().strip()
        by_full.setdefault(full, []).append(uid)
        if c.first_name:
            by_first.setdefault(c.first_name.lower().strip(), []).append(uid)

    unresolved = []
    for uid, contact in contacts.items():
        for rel in contact.raw_related:
            target_name = rel.name.lower().strip()
            label = rel.label

            # 1. Try nickname match first
            nick_candidates = [u for u in by_nickname.get(target_name, []) if u != uid]
            if len(nick_candidates) == 1:
                _apply_relation(contacts, uid, nick_candidates[0], label)
                continue

            # 2. Try full display name match
            candidates = [u for u in by_full.get(target_name, []) if u != uid]
            if len(candidates) == 1:
                _apply_relation(contacts, uid, candidates[0], label)
            else:
                # 3. Fall back to first-name match as a hint (still flag as ambiguous if >1)
                fname_candidates = [u for u in by_first.get(target_name, []) if u != uid]
                if len(fname_candidates) == 1 and not candidates:
                    _apply_relation(contacts, uid, fname_candidates[0], label)
                else:
                    if candidates or fname_candidates:
                        reason = "ambiguous"
                    elif all_contact_names and target_name in all_contact_names:
                        reason = "out_of_scope"
                    else:
                        reason = "not_found"
                    unresolved.append(
                        {
                            "contact_uid": uid,
                            "contact_name": contact.display_name,
                            "related_name": rel.name,
                            "label": label,
                            "candidates": candidates or fname_candidates,
                            "reason": reason,
                        }
                    )

    return unresolved


def infer_relationships(contacts: dict[str, Contact]) -> int:
    """
    Derive implied family links via multi-pass fixed-point inference.

    Rule 1 — sibling propagation:
        If A is a sibling of B and A has known parents, B inherits those parents.
    Rule 2 — shared-parent → siblings:
        If A and B share the same parents, mark them as siblings of each other.

    Repeats until no new links are added. Returns total number of links inferred.
    """
    total = 0
    while True:
        added = 0

        # Rule 1: propagate parents through sibling links
        for uid, contact in contacts.items():
            if not contact.parent_uids or not contact.sibling_uids:
                continue
            for sib_uid in contact.sibling_uids:
                if sib_uid not in contacts:
                    continue
                sib = contacts[sib_uid]
                for parent_uid in contact.parent_uids:
                    if parent_uid not in contacts:
                        continue
                    if parent_uid not in sib.parent_uids:
                        sib.parent_uids.append(parent_uid)
                        parent = contacts[parent_uid]
                        if sib_uid not in parent.children_uids:
                            parent.children_uids.append(sib_uid)
                        added += 1

        # Rule 2: contacts sharing the same parents are siblings
        parent_key_to_children: dict[tuple, list[str]] = {}
        for uid, contact in contacts.items():
            if contact.parent_uids:
                key = tuple(sorted(contact.parent_uids))
                parent_key_to_children.setdefault(key, []).append(uid)

        for siblings in parent_key_to_children.values():
            for uid_a in siblings:
                for uid_b in siblings:
                    if uid_a == uid_b:
                        continue
                    if uid_b not in contacts[uid_a].sibling_uids:
                        contacts[uid_a].sibling_uids.append(uid_b)
                        added += 1

        total += added
        if added == 0:
            break

    if total:
        logger.info(f"Inferred {total} additional family links")
    return total


PHOTOS_DIR = Path(__file__).parent / "data" / "photos"


def parse_contacts(
    vcf_text: str,
    groups_data: dict[str, list[str]],
    all_contact_names: set[str] | None = None,
) -> tuple[dict[str, Contact], list[dict]]:
    """
    Parse vCards, assign groups, resolve relationships.
    Returns (contacts_by_uid, unresolved_relations).
    """
    contacts: dict[str, Contact] = {}
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    for vcard in vobject.readComponents(vcf_text):
        if getattr(vcard, "name", "") != "VCARD":
            continue
        contact, photo_bytes = _parse_vcard(vcard)
        if contact:
            if photo_bytes:
                photo_path = PHOTOS_DIR / f"{contact.uid}.jpg"
                photo_path.write_bytes(photo_bytes)
                contact.photo_url = f"/photos/{contact.uid}.jpg"
            contacts[contact.uid] = contact

    # Assign Apple Contacts group memberships
    for group_name, uids in groups_data.items():
        for raw_uid in uids:
            uid = _normalize_uid(raw_uid)
            if uid in contacts and group_name not in contacts[uid].groups:
                contacts[uid].groups.append(group_name)

    unresolved = _resolve_relationships(contacts, all_contact_names)

    logger.info(
        f"Parsed {len(contacts)} contacts, {len(unresolved)} unresolved relations"
    )
    return contacts, unresolved
