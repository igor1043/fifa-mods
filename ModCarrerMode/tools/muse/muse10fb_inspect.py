#!/usr/bin/env python3
"""Read-only parser for the BIG4/MUSE/10FB laboratory format.

The active MUSE file contains a BIG4 directory whose entries use a six-byte
10FB envelope followed by an uncompressed-looking payload.  The two 16-bit
values in that envelope are reported but intentionally not regenerated: the
checksum/codec contract is not proven yet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path


def parse_big4(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] != b"BIG4":
        raise ValueError("not a BIG4 container")
    count, directory_size = struct.unpack_from(">II", data, 8)
    cursor = 16
    entries: list[dict] = []
    for index in range(count):
        if cursor + 8 > len(data):
            raise ValueError(f"directory truncated before entry {index}")
        offset, size = struct.unpack_from(">II", data, cursor)
        name_start = cursor + 8
        name_end = data.find(b"\0", name_start)
        if name_end < 0:
            raise ValueError(f"unterminated name at entry {index}")
        name = data[name_start:name_end].decode("latin1", "replace")
        cursor = name_end + 1
        payload = data[offset : offset + size]
        if len(payload) != size:
            raise ValueError(f"entry {index} exceeds container")
        entry = {
            "index": index,
            "name": name,
            "offset": offset,
            "size": size,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if payload.startswith(b"\x10\xfb") and len(payload) >= 6:
            body = payload[6:]
            entry["10fb"] = {
                "header_hex": payload[:6].hex(" "),
                "value_a_be": int.from_bytes(payload[2:4], "big"),
                "value_b_be": int.from_bytes(payload[4:6], "big"),
                "payload_size": len(body),
                "payload_prefix_hex": body[:16].hex(" "),
                "payload_ascii_prefix": body[:80].decode("latin1", "replace"),
            }
        entries.append(entry)
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "format": "BIG4",
        "entry_count": count,
        "directory_size_field": directory_size,
        "directory_cursor_after_names": cursor,
        "entries": entries,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = parse_big4(args.input)
    print(json.dumps(result, ensure_ascii=False,
                     indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
