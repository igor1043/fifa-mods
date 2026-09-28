#!/usr/bin/env python3
"""Persist a valid birth date in newly written FIFA 16 Player Career saves.

The watcher deliberately does not touch generic Career saves.  It only acts on
DATA files that contain the verified ``career_playasplayer`` and ``players``
tables.  Existing files are ignored until their size or modification time
changes after the watcher starts.  Every replacement is delegated to the
validated T3DB editor in ``birthdate_editor.py`` and receives an external
backup before the atomic replace.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from birthdate_editor import EditorError, commit_player_career_file, inspect_player_career_file


DEFAULT_FALLBACK_YEAR = 2006
DEFAULT_MIN_YEAR = 2006
DEFAULT_MAX_YEAR = 2012
DEFAULT_POLL_SECONDS = 0.75
DEFAULT_STABLE_POLLS = 3


def tool_dir() -> Path:
    if getattr(sys, "frozen", False):
        directory = Path(sys.executable).resolve().parent
        if directory.name.casefold() == "dist":
            return directory.parent
        return directory
    return Path(__file__).resolve().parent


def default_save_root() -> Path:
    profile = os.environ.get("USERPROFILE")
    if profile:
        return Path(profile) / "Documents" / "FIFA 16" / "0" / "FIFA16"
    return Path.home() / "Documents" / "FIFA 16" / "0" / "FIFA16"


def parse_year(value: str) -> int:
    try:
        year = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("year must be an integer") from exc
    if not 1900 <= year <= 2100:
        raise argparse.ArgumentTypeError("year must be between 1900 and 2100")
    return year


def data_files(root: Path) -> list[Path]:
    try:
        return sorted(
            (path for path in root.rglob("DATA") if path.is_file()),
            key=lambda path: str(path).casefold(),
        )
    except OSError:
        return []


def stat_signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_event(log_path: Path, event: str, **fields: object) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "time": dt.datetime.now().isoformat(timespec="seconds"),
        "event": event,
        **fields,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def baseline(root: Path) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for path in data_files(root):
        try:
            result[str(path.resolve()).casefold()] = stat_signature(path)
        except OSError:
            continue
    return result


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"save root not found: {root}")
    log_path = args.log.resolve()
    backup_dir = args.backup_dir.resolve()
    initial = baseline(root)
    started_ns = time.time_ns()
    stable: dict[str, tuple[tuple[int, int], int]] = {}
    processed_hashes: dict[str, str] = {}
    write_event(
        log_path,
        "started",
        root=str(root),
        allowedYears=f"{args.min_year}..{args.max_year}",
        fallbackDate=dt.date(args.fallback_year, 1, 1).isoformat(),
        existingDataFiles=len(initial),
        mode="apply",
    )

    while True:
        found_candidate = False
        completed_candidate = False
        for path in data_files(root):
            key = str(path.resolve()).casefold()
            try:
                signature = stat_signature(path)
            except OSError:
                continue
            old_signature = initial.get(key)
            if old_signature == signature:
                continue
            found_candidate = True
            previous = stable.get(key)
            count = previous[1] + 1 if previous and previous[0] == signature else 1
            stable[key] = (signature, count)
            if count < args.stable_polls:
                continue

            try:
                current_hash = file_hash(path)
                if processed_hashes.get(key) == current_hash:
                    continue
                info = inspect_player_career_file(path)
                saved_date = dt.date.fromisoformat(info["birthdate"])
                if args.min_year <= saved_date.year <= args.max_year:
                    target_date = saved_date
                    target_reason = "preserve-selected-year"
                else:
                    target_date = dt.date(args.fallback_year, 1, 1)
                    target_reason = "outside-range-fallback"
                if info["birthdate"] == target_date.isoformat() and info["isretiring"] == 0:
                    processed_hashes[key] = current_hash
                    completed_candidate = True
                    write_event(
                        log_path,
                        "already_correct",
                        path=str(path),
                        playerId=info["playerId"],
                        birthdate=info["birthdate"],
                    )
                    continue
                write_event(
                    log_path,
                    "player_career_detected",
                    path=str(path),
                    playerId=info["playerId"],
                    beforeBirthdate=info["birthdate"],
                    beforeSerial=info["birthdateSerial"],
                    targetDate=target_date.isoformat(),
                    targetReason=target_reason,
                )
                report = commit_player_career_file(path, target_date, backup_dir)
                processed_hashes[key] = file_hash(path)
                completed_candidate = True
                write_event(
                    log_path,
                    "patched",
                    path=str(path),
                    playerId=report["playerId"],
                    requestedDate=report["requestedDate"],
                    targetReason=target_reason,
                    targetStartingAge=report["targetStartingAge"],
                    backupPath=report.get("backupPath"),
                    outputSha256=report["outputSha256"],
                    integrity=report["integrity"],
                )
            except (EditorError, OSError) as exc:
                # A partially-written DATA or a file still being replaced is
                # retried on the next stable observation.  The log records
                # only one error per signature to avoid noise.
                marker = f"{signature[0]}:{signature[1]}"
                error_key = f"{key}:{marker}"
                if error_key not in processed_hashes:
                    processed_hashes[error_key] = "error"
                    write_event(log_path, "candidate_retry", path=str(path), error=str(exc))

        if args.once and completed_candidate:
            write_event(log_path, "once_finished")
            return 0
        time.sleep(args.poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_save_root(), help="FIFA 16 save root")
    parser.add_argument("--year", dest="fallback_year", type=parse_year, default=DEFAULT_FALLBACK_YEAR,
                        help="fallback January 1 year when the saved year is outside the allowed range")
    parser.add_argument("--min-year", type=parse_year, default=DEFAULT_MIN_YEAR)
    parser.add_argument("--max-year", type=parse_year, default=DEFAULT_MAX_YEAR)
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--stable-polls", type=int, default=DEFAULT_STABLE_POLLS)
    parser.add_argument("--log", type=Path, default=tool_dir() / "logs" / "birthdate_watcher_2006.log")
    parser.add_argument("--backup-dir", type=Path, default=tool_dir() / "backups")
    parser.add_argument("--once", action="store_true", help="stop after the first candidate pass")
    args = parser.parse_args()
    if args.poll_seconds <= 0 or args.stable_polls < 1 or args.max_year < args.min_year:
        parser.error("poll-seconds must be positive and stable-polls must be at least 1")
    if not args.min_year <= args.fallback_year <= args.max_year:
        parser.error("fallback year must be inside the allowed range")
    return run(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
