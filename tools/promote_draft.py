#!/usr/bin/env python3
"""
promote_draft.py - promote a generated bid draft into active bid work.

The draft generator writes regenerable files to build/drafts/. This tool
copies one of those drafts into bids/active/<opportunity-id>.md after
verifying that the opportunity is still active in the pipeline. It
refuses to overwrite committed bid markdown unless --force is passed.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv"
DEFAULT_DRAFT_DIR = REPO_ROOT / "build" / "drafts"
DEFAULT_ACTIVE_DIR = REPO_ROOT / "bids" / "active"
DEFAULT_ARCHIVE_DIR = REPO_ROOT / "bids" / "archive"
OPEN_STATUSES = {"watching", "drafting", "submitted"}

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import read_rows  # noqa: E402


def _find_row(rows: list[dict], opportunity_id: str) -> dict | None:
    for row in rows:
        if (row.get("opportunity_id") or "").strip() == opportunity_id:
            return row
    return None


def validate_promotion(
    opportunity_id: str,
    active_path: Path,
    archive_path: Path,
    draft_path: Path,
    dest_path: Path,
    archive_dest_path: Path,
    force: bool,
) -> dict:
    """Return the active pipeline row, or raise ValueError/OSError."""
    _, active_rows = read_rows(active_path)
    _, archive_rows = read_rows(archive_path)
    active_row = _find_row(active_rows, opportunity_id)
    archive_row = _find_row(archive_rows, opportunity_id)

    if archive_row is not None:
        raise ValueError(f"{opportunity_id!r} is already in the archive pipeline")
    if active_row is None:
        raise ValueError(f"{opportunity_id!r} was not found in the active pipeline")
    status = (active_row.get("status") or "").strip().lower()
    if status and status not in OPEN_STATUSES:
        raise ValueError(f"{opportunity_id!r} has non-active status {status!r}")
    if not draft_path.is_file():
        raise FileNotFoundError(f"draft not found: {draft_path}")
    if dest_path.exists() and not force:
        raise FileExistsError(f"{dest_path} already exists. Pass --force to overwrite.")
    if archive_dest_path.exists() and not force:
        raise FileExistsError(
            f"{archive_dest_path} already exists in archive. "
            "Pass --force only if you are intentionally reactivating work."
        )
    return active_row


def atomic_copy_text(src: Path, dest: Path) -> None:
    """Copy UTF-8 text using an atomic replace in the destination dir."""
    content = src.read_text(encoding="utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=dest.stem + ".", suffix=".tmp", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp, dest)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("opportunity_id", help="Pipeline opportunity_id to promote.")
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE), help="Active pipeline CSV (default: %(default)s)")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="Archive pipeline CSV (default: %(default)s)")
    parser.add_argument("--draft-dir", default=str(DEFAULT_DRAFT_DIR), help="Directory containing <id>_draft.md")
    parser.add_argument("--active-dir", default=str(DEFAULT_ACTIVE_DIR), help="Destination directory for active bid markdown")
    parser.add_argument("--archive-dir", default=str(DEFAULT_ARCHIVE_DIR), help="Archive markdown directory checked for collisions")
    parser.add_argument("--draft", default=None, help="Explicit draft path; overrides --draft-dir.")
    parser.add_argument("--output", default=None, help="Explicit destination path; defaults to active-dir/<id>.md.")
    parser.add_argument("--force", action="store_true", help="Overwrite destination markdown if it already exists.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    opportunity_id = args.opportunity_id
    draft_path = Path(args.draft) if args.draft else Path(args.draft_dir) / f"{opportunity_id}_draft.md"
    dest_path = Path(args.output) if args.output else Path(args.active_dir) / f"{opportunity_id}.md"
    archive_dest_path = Path(args.archive_dir) / f"{opportunity_id}.md"

    try:
        row = validate_promotion(
            opportunity_id=opportunity_id,
            active_path=Path(args.active),
            archive_path=Path(args.archive),
            draft_path=draft_path,
            dest_path=dest_path,
            archive_dest_path=archive_dest_path,
            force=args.force,
        )
        atomic_copy_text(draft_path, dest_path)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"promoted:    {opportunity_id}")
    print(f"status:      {(row.get('status') or '').strip() or '(blank)'}")
    print(f"source:      {draft_path}")
    print(f"destination: {dest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
