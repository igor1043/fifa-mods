#!/usr/bin/env python3
"""Read-only reconnaissance parser for FIFA 16 CRWD/chunkzip files.

This tool deliberately does not rewrite crowd assets.  CRWD's complete
record semantics are not known yet; the report exposes the stable header,
32-byte sampling boundaries, trailing bytes, and optional _1/_3 differences
so new captures can be compared without damaging the installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def u32be(data: bytes, offset: int) -> int | None:
    if offset + 4 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 4], "big")


def runs(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    result: list[list[int]] = []
    start = previous = values[0]
    for value in values[1:]:
        if value != previous + 1:
            result.append([start, previous])
            start = value
        previous = value
    result.append([start, previous])
    return result


def inspect(path: Path, pair: Path | None = None) -> dict:
    data = path.read_bytes()
    magic = data[:8].decode("latin1", "replace")
    result: dict = {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "magic": magic,
        "header_hex": data[:32].hex(" "),
    }
    if data.startswith(b"CRWD"):
        result.update(
            {
                "format": "CRWD",
                "version_hex": data[4:6].hex(" "),
                "header_word_hex": data[6:8].hex(" "),
                "u32be_at_8": u32be(data, 8),
                "u32be_at_12": u32be(data, 12),
                "sample_offset": 32,
                "sample_stride": 32,
                "sample_count": max(0, (len(data) - 32) // 32),
                "sample_tail_bytes": max(0, (len(data) - 32) % 32),
            }
        )
    elif data.startswith(b"chunkzip"):
        result.update(
            {
                "format": "chunkzip",
                "u32be_at_8": u32be(data, 8),
                "u32be_at_12": u32be(data, 12),
                "u32be_at_16": u32be(data, 16),
                "u32be_at_20": u32be(data, 20),
                "u32be_at_24": u32be(data, 24),
            }
        )
    else:
        result["format"] = "unknown"

    if pair is not None:
        other = pair.read_bytes()
        values = [i for i, (a, b) in enumerate(zip(data, other)) if a != b]
        if len(data) != len(other):
            values.extend(range(min(len(data), len(other)), max(len(data), len(other))))
        result["pair"] = {
            "path": str(pair),
            "size": len(other),
            "sha256": hashlib.sha256(other).hexdigest(),
            "different_bytes": len(values),
            "difference_runs": runs(values),
            "difference_offsets_mod32": sorted({value % 32 for value in values}),
        }
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--pair", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    print(json.dumps(inspect(args.input, args.pair), ensure_ascii=False,
                     indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
