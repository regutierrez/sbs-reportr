"""Generate an incomplete report via the API.

Usage:
    uv run python generate_incomplete_report.py --entry-id 1
    uv run python generate_incomplete_report.py --entry-id 17 --base-url http://localhost:3000
    uv run python generate_incomplete_report.py --entry-id 1 --output my-report.pdf
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://noco:9999"

JSON_FILE = Path(__file__).resolve().parent / "PSRRRP Firm 3 - List of for reporting_v2.json"

# Map API image-group names to local file/folder paths (relative to --photo-dir).
IMAGE_GROUPS: dict[str, str] = {
    "building_details_building_photo": "building-photo.jpeg",
    "superstructure_rebar_scanning_photos": "rebar-scanning-photos",
    "superstructure_rebound_hammer_test_photos": "rebound-hammer-photos",
    "superstructure_concrete_coring_photos": "concrete-coring-photos",
    "superstructure_core_samples_family_pic": "core-samples-family-photos",
    "superstructure_rebar_extraction_photos": "rebar-extraction-photos",
    "superstructure_rebar_samples_family_pic": "rebar-samples-family-photo",
    "superstructure_chipping_of_slab_photos": "chipping-of-slab-photos",
    "superstructure_restoration_photos": "restoration-photos",
    "substructure_coring_for_foundation_photos": "foundation-coring-photos",
    "substructure_rebar_scanning_for_foundation_photos": "foundation-rebar-scanning-photos",
    "substructure_restoration_backfilling_compaction_photos": "restoration-backfilling-compaction-photos",
}


# ---------------------------------------------------------------------------
# Build the API payload from a JSON entry
# ---------------------------------------------------------------------------


def _load_entry(entry_id: int) -> dict:
    entries = json.loads(JSON_FILE.read_text())
    for entry in entries:
        if entry["__EMPTY"] == entry_id:
            return entry
    available = [e["__EMPTY"] for e in entries]
    print(f"ERROR: No entry with __EMPTY={entry_id}. Available: {available}", file=sys.stderr)
    sys.exit(1)


def _build_payload(entry: dict) -> dict:
    """Convert a JSON entry into the API form payload."""
    payload: dict = {
        "building_details": {
            "testing_date": entry["Testing Date"],
            "building_name": entry["Building Name"],
            "building_location": entry["Building Location"],
            "number_of_storey": entry["Number of Storey"],
        },
        "superstructure": {
            "rebar_scanning": {
                "number_of_rebar_scan_locations": entry["Rebar Scan Locations"],
            },
            "rebound_hammer_test": {
                "number_of_rebound_hammer_test_locations": entry["Rebound Hammer Test Locations"],
            },
            "concrete_core_extraction": {
                "number_of_coring_locations": entry["Coring Locations"],
            },
            "rebar_extraction": {
                "number_of_rebar_samples_extracted": entry["Number of rebar samples"],
            },
            "restoration_works": {
                "non_shrink_grout_product_used": entry["Non-shrink Grout Product"],
                "epoxy_ab_used": entry["Epoxy A&B Product"],
            },
        },
        "signature": {},
    }

    # Substructure (optional)
    if entry.get("Foundation Locations") is not None:
        payload["substructure"] = {
            "concrete_core_extraction": {
                "number_of_foundation_locations": entry["Foundation Locations"],
                "number_of_foundation_cores_extracted": entry.get(
                    "Number of extracted cores", entry["Foundation Locations"]
                ),
            },
        }

    # Signature — prefer Inspector fields, fall back to Prepared By / Role
    prepared_by = entry.get("Inspector") or entry.get("Prepared By")
    prepared_by_role = entry.get("Inspector Title") or entry.get("Role")
    if prepared_by:
        payload["signature"]["prepared_by"] = prepared_by
    if prepared_by_role:
        payload["signature"]["prepared_by_role"] = prepared_by_role

    return payload


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _post(url: str, body: dict[str, object] | None = None) -> dict[str, object]:
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        detail = exc.read().decode()
        print(f"  ERROR {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)


def _put(url: str, body: dict[str, object]) -> dict[str, object]:
    data = json.dumps(body).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="PUT")
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        detail = exc.read().decode()
        print(f"  ERROR {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)


def _upload_image(url: str, filepath: Path) -> None:
    """Upload a single image file as multipart/form-data."""
    boundary = uuid.uuid4().hex
    content_type = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
    filename = filepath.name
    file_data = filepath.read_bytes()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n"
        f"\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlopen(req) as resp:
            resp.read()
    except HTTPError as exc:
        detail = exc.read().decode()
        print(f"  ERROR {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)


def _download(url: str, dest: Path) -> None:
    req = Request(url, method="GET")
    try:
        with urlopen(req) as resp:
            dest.write_bytes(resp.read())
    except HTTPError as exc:
        detail = exc.read().decode()
        print(f"  ERROR {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)


def _collect_images(photo_dir: Path, local_path: str) -> list[Path]:
    """Return a list of image file paths for a given local_path entry."""
    target = photo_dir / local_path
    if not target.exists():
        return []
    if target.is_file():
        return [target]
    return sorted(
        p for p in target.iterdir() if p.suffix.lower() in {".jpeg", ".jpg", ".png"}
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an incomplete report.")
    parser.add_argument(
        "--entry-id", type=int, required=True,
        help="Entry ID (__EMPTY value) from the JSON data file",
    )
    parser.add_argument("--base-url", default=BASE_URL, help=f"API base URL (default: {BASE_URL})")
    parser.add_argument(
        "--output", default="report.pdf", help="Output PDF path (default: report.pdf)"
    )
    parser.add_argument(
        "--photo-dir",
        default=str(Path(__file__).resolve().parent / "test"),
        help="Directory containing photo folders (default: ./test)",
    )
    args = parser.parse_args()

    base: str = args.base_url.rstrip("/")
    output = Path(args.output)
    photo_dir = Path(args.photo_dir)

    print(f"Loading entry {args.entry_id} from {JSON_FILE.name}...")
    entry = _load_entry(args.entry_id)
    payload = _build_payload(entry)
    print(f"   Building: {entry['Building Name']}")

    print("1. Creating session...")
    session = _post(f"{base}/reports")
    session_id = session["session_id"]
    print(f"   Session: {session_id}")

    print("2. Saving form fields...")
    _put(f"{base}/reports/{session_id}", payload)
    print("   Done.")

    print("3. Uploading photos...")
    uploaded_count = 0
    for group_name, local_path in IMAGE_GROUPS.items():
        files = _collect_images(photo_dir, local_path)
        if not files:
            print(f"   Skipping {group_name} (no files found at {photo_dir / local_path})")
            continue
        for img_file in files:
            _upload_image(f"{base}/reports/{session_id}/images/{group_name}", img_file)
            uploaded_count += 1
        print(f"   ✓ {group_name} ({len(files)} file{'s' if len(files) != 1 else ''})")
    print(f"   Uploaded {uploaded_count} image(s) total.")

    print("4. Generating incomplete report...")
    result = _post(f"{base}/reports/{session_id}/generate-incomplete")
    download_url = result["download_url"]
    print(f"   Download URL: {download_url}")

    print(f"5. Downloading to {output}...")
    _download(f"{base}{download_url}", output)
    print(f"   Saved {output} ({output.stat().st_size:,} bytes)")

    print(f"\nDone! (session: {session_id})")


if __name__ == "__main__":
    main()