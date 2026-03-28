"""
Applies the enrichment.yaml overlay on top of parsed contacts.
Enrichment lets you:
  - Define explicit UID-based relationships (overrides auto-resolved ones)
  - Assign contacts to groups not stored in Apple Contacts
  - Add structured interests per contact
  - Add extra notes
"""
import logging
from pathlib import Path

import yaml

from models import Contact
from parser import infer_relationships

logger = logging.getLogger(__name__)


def load_enrichment(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def apply_enrichment(
    contacts: dict[str, Contact], enrichment_path: Path
) -> dict[str, Contact]:
    data = load_enrichment(enrichment_path)
    if not data:
        return contacts

    # 1. Explicit UID-based relationships (override auto-resolved)
    for rel in data.get("relationships", []):
        from_uid = rel.get("from_uid", "").strip()
        to_uid = rel.get("to_uid", "").strip()
        rel_type = rel.get("type", "").strip().lower()
        if from_uid not in contacts or to_uid not in contacts:
            logger.warning(f"Enrichment relationship references unknown UID: {from_uid} → {to_uid}")
            continue

        src = contacts[from_uid]
        tgt = contacts[to_uid]

        if rel_type in ("spouse", "partner"):
            src.spouse_uid = to_uid
            tgt.spouse_uid = from_uid
        elif rel_type == "child":
            if to_uid not in src.children_uids:
                src.children_uids.append(to_uid)
            if from_uid not in tgt.parent_uids:
                tgt.parent_uids.append(from_uid)
        elif rel_type == "parent":
            if to_uid not in src.parent_uids:
                src.parent_uids.append(to_uid)
            if from_uid not in tgt.children_uids:
                tgt.children_uids.append(from_uid)

    # 2. Family declarations — explicit parent/child sets
    for family_name, family in data.get("families", {}).items():
        parent_uids = [u.strip() for u in (family.get("parents") or []) if u.strip() in contacts]
        child_uids  = [u.strip() for u in (family.get("children") or []) if u.strip() in contacts]

        unknown = [u.strip() for u in (family.get("parents", []) + family.get("children", []))
                   if u.strip() not in contacts]
        if unknown:
            logger.warning(f"Family '{family_name}' references unknown UIDs: {unknown}")

        for child_uid in child_uids:
            child = contacts[child_uid]
            for parent_uid in parent_uids:
                if parent_uid not in child.parent_uids:
                    child.parent_uids.append(parent_uid)
                parent = contacts[parent_uid]
                if child_uid not in parent.children_uids:
                    parent.children_uids.append(child_uid)

        # Siblings within the family
        for uid_a in child_uids:
            for uid_b in child_uids:
                if uid_a != uid_b and uid_b not in contacts[uid_a].sibling_uids:
                    contacts[uid_a].sibling_uids.append(uid_b)

    # 3. Group assignments
    for group_name, uids in data.get("groups", {}).items():
        for uid in (uids or []):
            uid = uid.strip()
            if uid in contacts and group_name not in contacts[uid].groups:
                contacts[uid].groups.append(group_name)

    # 3. Per-contact enrichment
    for uid, extra in data.get("contacts", {}).items():
        uid = uid.strip()
        if uid not in contacts:
            logger.warning(f"Enrichment references unknown contact UID: {uid}")
            continue
        c = contacts[uid]
        if "interests" in extra:
            c.interests = list(extra["interests"])
        if "notes_extra" in extra and extra["notes_extra"]:
            suffix = str(extra["notes_extra"]).strip()
            c.notes = f"{c.notes}\n\n{suffix}".strip() if c.notes else suffix

    # Run inference after all explicit + family links are in place
    infer_relationships(contacts)

    logger.info("Enrichment applied")
    return contacts
