#!/usr/bin/env python3
"""
sync_photos.py — Set Apple Contacts photos from Apple Photos People album.

Usage:
    python3 sync_photos.py            # dry run: show matches only
    python3 sync_photos.py --apply    # actually set photos in Apple Contacts
    python3 sync_photos.py --apply --no-crop  # use full key photo, skip face crop
    python3 sync_photos.py --apply --person "Jane Doe"  # process one person only

Requirements:
    pip3 install osxphotos pillow

How it works:
    1. Reads named persons from Apple Photos' People album via osxphotos
    2. Gets the best face crop for each person (falls back to key photo if unavailable)
    3. Fetches all Apple Contacts names via AppleScript
    4. Matches by name (case-insensitive, exact full name)
    5. In --apply mode: exports cropped photo to temp file, sets it on the contact
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


def check_pillow():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def convert_heic_to_jpeg(heic_path: str, dest_dir: str) -> str | None:
    """Convert a HEIC file to JPEG using macOS sips. Returns JPEG path or None."""
    out_path = os.path.join(dest_dir, os.path.basename(heic_path).rsplit(".", 1)[0] + "_converted.jpg")
    proc = subprocess.run(
        ["sips", "-s", "format", "jpeg", heic_path, "--out", out_path],
        capture_output=True, text=True
    )
    return out_path if proc.returncode == 0 and os.path.exists(out_path) else None


def get_photos_persons(osxphotos):
    """Return list of (name, person) tuples from Photos People album."""
    db = osxphotos.PhotosDB()
    persons = []
    for person in db.person_info:
        name = person.name
        if not name or name.strip() == "":
            continue
        if person.keyphoto is None:
            continue
        persons.append((name.strip(), person))
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
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=120
    )
    if proc.returncode != 0:
        print(f"ERROR: AppleScript failed: {proc.stderr.strip()}")
        sys.exit(1)

    contacts = {}
    raw = proc.stdout.strip()
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


def set_contact_photo_applescript(contact_id: str, photo_path: str) -> tuple[bool, str]:
    """Set the photo of a contact by ID using AppleScript. Returns (ok, error)."""
    safe_path = photo_path.replace('"', '\\"')
    script = f'''
    tell application "Contacts"
        set thePerson to person id "{contact_id}"
        if image of thePerson is not missing value then
            delete image of thePerson
        end if
        set theImage to (read POSIX file "{safe_path}" as JPEG picture)
        set image of thePerson to theImage
        save
    end tell
    '''
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=30
    )
    return proc.returncode == 0, proc.stderr.strip()


def export_keyphoto(keyphoto, dest_dir: str) -> str | None:
    """Export the key photo to dest_dir as JPEG. Returns path or None."""
    try:
        paths = keyphoto.export(dest_dir, use_photos_export=False, overwrite=True)
        if paths:
            return paths[0]
    except Exception as e:
        print(f"  WARNING: export failed: {e}")
    return None


def export_face_crop(person, dest_dir: str, Image) -> str | None:
    """
    Export a face-cropped portrait for the person to dest_dir.
    Uses the highest-quality face detection bounding box.
    Returns path to cropped JPEG, or None if not possible.
    """
    if not person.face_info:
        return None

    # face_info is sorted by quality, best first; find one with a local photo
    face = None
    for f in person.face_info:
        if f.photo and f.photo.path:
            face = f
            break

    if face is None:
        return None

    try:
        rect = face.face_rect()  # [(x, y), (x2, y2)] pixel coords, top-left origin
        if not rect or len(rect) < 2:
            return None

        from PIL import ImageOps
        photo_path = face.photo.path
        if photo_path.lower().endswith(".heic"):
            converted = convert_heic_to_jpeg(photo_path, dest_dir)
            if converted is None:
                return None
            photo_path = converted
        img = ImageOps.exif_transpose(Image.open(photo_path))
        w, h = img.size

        x1, y1 = rect[0]
        x2, y2 = rect[1]
        face_w = x2 - x1
        face_h = y2 - y1

        # Add padding around the detected face region
        pad_x = face_w * 0.4
        pad_y = face_h * 0.5

        cx = int(max(0, x1 - pad_x))
        cy = int(max(0, y1 - pad_y))
        cx2 = int(min(w, x2 + pad_x))
        cy2 = int(min(h, y2 + pad_y))

        cropped = img.crop((cx, cy, cx2, cy2))
        out_path = os.path.join(dest_dir, f"face_{face.photo.uuid}.jpg")
        cropped.convert("RGB").save(out_path, "JPEG", quality=90)
        return out_path

    except Exception as e:
        print(f"  WARNING: face crop failed: {e}")
        return None


def normalize_name(name: str) -> str:
    return name.strip().lower()


def main():
    parser = argparse.ArgumentParser(description="Sync Apple Photos person photos to Apple Contacts")
    parser.add_argument("--apply", action="store_true", help="Actually set photos (default: dry run)")
    parser.add_argument("--no-crop", action="store_true", help="Use full key photo instead of face crop")
    parser.add_argument("--verbose", action="store_true", help="Show all unmatched contacts too")
    parser.add_argument("--person", metavar="NAME", help="Only process this person (case-insensitive full name)")
    args = parser.parse_args()

    osxphotos = check_osxphotos()

    use_crop = not args.no_crop
    Image = None
    if use_crop:
        Image = check_pillow()
        if Image is None:
            print("WARNING: Pillow is not installed — falling back to full key photo.")
            print("Install it with:  pip3 install pillow")
            use_crop = False

    print("Reading Apple Photos People album…")
    persons = get_photos_persons(osxphotos)
    print(f"  Found {len(persons)} named persons with key photos in Photos")

    print("Reading Apple Contacts…")
    contacts = get_contacts_via_applescript()
    print(f"  Found {len(contacts)} contacts")

    # Build lookup: lowercase name → (original_name, uid)
    contacts_lower = {normalize_name(k): (k, v) for k, v in contacts.items()}

    matched = []
    unmatched_photos = []

    for photo_name, person in persons:
        key = normalize_name(photo_name)
        if key in contacts_lower:
            orig_name, uid = contacts_lower[key]
            matched.append((photo_name, orig_name, uid, person))
        else:
            unmatched_photos.append(photo_name)

    if args.person:
        filter_key = normalize_name(args.person)
        matched = [m for m in matched if normalize_name(m[0]) == filter_key]
        if not matched:
            print(f"\nNo match found for '{args.person}'. Check spelling or run without --person to see all matches.")
            return

    print(f"\nMatched:   {len(matched)}")
    print(f"Unmatched: {len(unmatched_photos)} (Photos persons with no matching contact)")

    if not matched:
        print("\nNo matches found. Nothing to do.")
        return

    if not args.apply:
        print("\n--- DRY RUN (pass --apply to set photos) ---\n")
        crop_label = "face-cropped" if use_crop else "key photo"
        print(f"Would set photos for ({crop_label}):")
        for photo_name, contact_name, uid, _ in matched:
            print(f"  {photo_name}  →  {contact_name}")
        if args.verbose and unmatched_photos:
            print(f"\nUnmatched Photos persons:")
            for name in sorted(unmatched_photos):
                print(f"  {name}")
        return

    # Apply mode
    crop_label = "face-cropped" if use_crop else "key photo"
    print(f"\n--- APPLYING {len(matched)} photos ({crop_label}) ---\n")
    success = 0
    failed = 0
    cropped_count = 0
    fallback_count = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for photo_name, contact_name, uid, person in matched:
            print(f"  {photo_name}…", end=" ", flush=True)

            exported_path = None

            if use_crop:
                exported_path = export_face_crop(person, tmpdir, Image)
                if exported_path:
                    cropped_count += 1
                else:
                    # Fall back to key photo
                    exported_path = export_keyphoto(person.keyphoto, tmpdir)
                    if exported_path:
                        fallback_count += 1
            else:
                exported_path = export_keyphoto(person.keyphoto, tmpdir)

            if not exported_path:
                print("SKIP (export failed)")
                failed += 1
                continue

            ok, err = set_contact_photo_applescript(uid, exported_path)
            if ok:
                print("OK")
                success += 1
            else:
                print(f"FAILED: {err}")
                failed += 1

    print(f"\nDone. {success} photos set, {failed} failed.")
    if use_crop:
        print(f"  Face-cropped: {cropped_count}, fell back to key photo: {fallback_count}")
    if failed > 0:
        print("Note: Some failures may be due to macOS privacy permissions.")
        print("Check System Settings > Privacy & Security > Contacts")

    if args.verbose and unmatched_photos:
        print(f"\nUnmatched Photos persons (no contact found):")
        for name in sorted(unmatched_photos):
            print(f"  {name}")


if __name__ == "__main__":
    main()
