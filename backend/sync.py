"""
Exports contacts and groups from Apple Contacts via AppleScript.
"""
import subprocess
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
ENRICHMENT_FILE = DATA_DIR / "enrichment.yaml"


def _load_sync_groups() -> list[str]:
    """Read sync_groups from enrichment.yaml. Returns [] (=all) if not set."""
    if not ENRICHMENT_FILE.exists():
        return []
    try:
        data = yaml.safe_load(ENRICHMENT_FILE.read_text(encoding="utf-8")) or {}
        groups = data.get("sync_groups", [])
        return [g for g in (groups or []) if g]
    except Exception as e:
        logger.warning(f"Could not read sync_groups from enrichment.yaml: {e}")
        return []


def _build_vcards_script(group_names: list[str]) -> str:
    """
    Build an AppleScript that exports vCards.
    If group_names is given, only export members of those groups (fast).
    Otherwise export all contacts (slow).
    """
    if not group_names:
        return """
tell application "Contacts"
    set allVcards to ""
    repeat with p in every person
        set allVcards to allVcards & (vcard of p)
    end repeat
    return allVcards
end tell
"""
    # Build a quoted list literal for AppleScript: {"Group A", "Group B", ...}
    quoted = ", ".join(f'"{g}"' for g in group_names)
    return f"""
tell application "Contacts"
    set wantedGroups to {{{quoted}}}
    set seen to {{}}
    set allVcards to ""
    repeat with gName in wantedGroups
        try
            set g to group gName
            repeat with p in every person of g
                set uid to id of p as string
                if uid is not in seen then
                    set end of seen to uid
                    set allVcards to allVcards & (vcard of p)
                end if
            end repeat
        end try
    end repeat
    return allVcards
end tell
"""


def _build_groups_script(group_names: list[str]) -> str:
    """
    Build an AppleScript that exports group membership as tab-separated lines.
    If group_names is given, only export those groups.
    """
    if not group_names:
        return """
tell application "Contacts"
    set output to ""
    repeat with g in every group
        set gName to name of g
        repeat with p in every person of g
            set output to output & gName & tab & (id of p as string) & linefeed
        end repeat
    end repeat
    return output
end tell
"""
    quoted = ", ".join(f'"{g}"' for g in group_names)
    return f"""
tell application "Contacts"
    set wantedGroups to {{{quoted}}}
    set output to ""
    repeat with gName in wantedGroups
        try
            set g to group gName
            repeat with p in every person of g
                set output to output & gName & tab & (id of p as string) & linefeed
            end repeat
        end try
    end repeat
    return output
end tell
"""


def _run_applescript(script: str, timeout: int = 180) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout


def export_vcards(group_names: list[str] | None = None) -> str:
    if group_names is None:
        group_names = _load_sync_groups()
    if group_names:
        logger.info(f"Exporting vCards for {len(group_names)} groups: {', '.join(group_names)}")
    else:
        logger.info("Exporting ALL vCards from Apple Contacts (may take a moment)...")
    script = _build_vcards_script(group_names)
    vcf_text = _run_applescript(script, timeout=300)
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "contacts.vcf").write_text(vcf_text, encoding="utf-8")
    logger.info("vCards exported")
    return vcf_text


def export_groups(group_names: list[str] | None = None) -> dict[str, list[str]]:
    if group_names is None:
        group_names = _load_sync_groups()
    if group_names:
        logger.info(f"Exporting groups: {', '.join(group_names)}")
    else:
        logger.info("Exporting all groups from Apple Contacts...")
    script = _build_groups_script(group_names)
    output = _run_applescript(script, timeout=60)
    groups: dict[str, list[str]] = {}
    for line in output.strip().splitlines():
        if "\t" in line:
            name, uid = line.split("\t", 1)
            name, uid = name.strip(), uid.strip()
            if name and uid:
                groups.setdefault(name, []).append(uid)
    logger.info(f"Found {len(groups)} groups")
    return groups


def export_all_names() -> set[str]:
    """Return display names of ALL contacts in Apple Contacts (not filtered by group)."""
    script = """
tell application "Contacts"
    set output to ""
    repeat with p in every person
        set n to name of p
        if n is not missing value then
            set output to output & n & "\n"
        end if
    end repeat
    output
end tell
"""
    raw = _run_applescript(script)
    return {line.strip().lower() for line in raw.splitlines() if line.strip()}


def sync_all() -> tuple[str, dict[str, list[str]], set[str]]:
    """Run all exports and return (vcf_text, groups_dict, all_contact_names)."""
    import json
    group_names = _load_sync_groups()
    vcf_text = export_vcards(group_names)
    groups = export_groups(group_names)
    all_names = export_all_names()
    (DATA_DIR / "all_names.json").write_text(json.dumps(sorted(all_names)))
    return vcf_text, groups, all_names
