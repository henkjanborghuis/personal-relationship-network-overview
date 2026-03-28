#!/usr/bin/env python3
"""
sync_photos.py — Set Apple Contacts photos from Apple Photos People album.

Usage:
    python3 sync_photos.py            # dry run: show matches only
    python3 sync_photos.py --apply    # actually set photos in Apple Contacts

Requirements:
    pip3 install osxphotos

How it works:
    1. Reads named persons from Apple Photos' People album via osxphotos
    2. Gets each person's key (representative) photo
    3. Fetches all Apple Contacts names via AppleScript
    4. Matches by name (case-insensitive, exact full name)
    5. In --apply mode: exports key photo to temp file, sets it on the contact
"""

import argparse
import subprocess
import sys
import tempfile
import os
from pathlib import Path


def check_osxphotos():
    try:
        import osxphotos
        return osxphotos
    except ImportError:
        print("ERROR: osxphotos is not installed.")
        print("Install it with:  pip3 install osxphotos")
        sys.exit(1)


def get_photos_persons(osxphotos):
    """Return list of (name, keyphoto) tuples from Photos People album."""
    db = osxphotos.PhotosDB()
    persons = []
    for person in db.person_info:
        name = person.name
        if not name or name.strip() == "":
            continue
        keyphoto = person.keyphoto
        if keyphoto is None:
            continue
        persons.append((name.strip(), keyphoto))
    return persons


def get_contacts_via_applescript():
    """Return dict of {full_name: contact_id} for all Apple Contacts."""
    script = '''
    tell application "Contacts"
        set contactList to {}
        repeat with p in every person
            set n to name of p
            set uid to id of p
            set end of contactList to (n & "||" & uid)
        end repeat
        return contactList
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"ERROR: AppleScript failed: {result.stderr.strip()}")
        sys.exit(1)

    contacts = {}
    # osascript returns comma-separated list
    raw = result.stdout.strip()
    if not raw:
        return contacts

    for item in raw.split(", "):
        item = item.strip()
        if "||" in item:
            parts = item.split("||", 1)
            name = parts[0].strip()
            uid = parts[1].strip()
            contacts[name] = uid

    return contacts


def set_contact_photo_applescript(contact_id: str, photo_path: str) -> bool:
    """Set the photo of a contact by ID using AppleScript. Returns True on success."""
    # Escape the path for AppleScript
    safe_path = photo_path.replace('"', '\\"')
    script = f'''
    tell application "Contacts"
        set thePerson to person id "{contact_id}"
        set theImage to (read POSIX file "{safe_path}" as JPEG picture)
        set image of thePerson to theImage
        save
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0, result.stderr.strip()


def export_keyphoto(keyphoto, dest_dir: str) -> str | None:
    """Export the key photo to dest_dir as JPEG. Returns path or None."""
    try:
        paths = keyphoto.export(dest_dir, use_photos_export=False, overwrite=True)
        if paths:
            return paths[0]
    except Exception as e:
        print(f"  WARNING: export failed: {e}")
    return None


def normalize_name(name: str) -> str:
    return name.strip().lower()


def main():
    parser = argparse.ArgumentParser(description="Sync Apple Photos person photos to Apple Contacts")
    parser.add_argument("--apply", action="store_true", help="Actually set photos (default: dry run)")
    parser.add_argument("--verbose", action="store_true", help="Show all unmatched contacts too")
    args = parser.parse_args()

    osxphotos = check_osxphotos()

    print("Reading Apple Photos People album…")
    persons = get_photos_persons(osxphotos)
    print(f"  Found {len(persons)} named persons with key photos in Photos")

    print("Reading Apple Contacts…")
    contacts = get_contacts_via_applescript()
    print(f"  Found {len(contacts)} contacts")

    # Build lookup: lowercase name → (original_name, uid)
    contacts_lower = {normalize_name(k): (k, v) for k, v in contacts.items()}

    # Match
    matched = []
    unmatched_photos = []

    for photo_name, keyphoto in persons:
        key = normalize_name(photo_name)
        if key in contacts_lower:
            orig_name, uid = contacts_lower[key]
            matched.append((photo_name, orig_name, uid, keyphoto))
        else:
            unmatched_photos.append(photo_name)

    print(f"\nMatched:   {len(matched)}")
    print(f"Unmatched: {len(unmatched_photos)} (Photos persons with no matching contact)")

    if not matched:
        print("\nNo matches found. Nothing to do.")
        return

    if not args.apply:
        print("\n--- DRY RUN (pass --apply to set photos) ---\n")
        print("Would set photos for:")
        for photo_name, contact_name, uid, _ in matched:
            print(f"  {photo_name}  →  {contact_name}")
        if args.verbose and unmatched_photos:
            print(f"\nUnmatched Photos persons:")
            for name in sorted(unmatched_photos):
                print(f"  {name}")
        return

    # Apply mode
    print(f"\n--- APPLYING {len(matched)} photos ---\n")
    success = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for photo_name, contact_name, uid, keyphoto in matched:
            print(f"  {photo_name}…", end=" ", flush=True)

            # Export photo to temp dir
            exported_path = export_keyphoto(keyphoto, tmpdir)
            if not exported_path:
                print("SKIP (export failed)")
                failed += 1
                continue

            # If not JPEG, we still try (osascript 'as JPEG picture' will handle conversion for common formats)
            ok, err = set_contact_photo_applescript(uid, exported_path)
            if ok:
                print("OK")
                success += 1
            else:
                print(f"FAILED: {err}")
                failed += 1

    print(f"\nDone. {success} photos set, {failed} failed.")
    if failed > 0:
        print("Note: Some failures may be due to macOS privacy permissions.")
        print("Check System Settings > Privacy & Security > Contacts")

    if args.verbose and unmatched_photos:
        print(f"\nUnmatched Photos persons (no contact found):")
        for name in sorted(unmatched_photos):
            print(f"  {name}")


if __name__ == "__main__":
    main()
