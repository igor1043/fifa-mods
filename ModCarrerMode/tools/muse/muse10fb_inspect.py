#!/usr/bin/env python3
"""Read-only BIG4/MUSE inspector with actual RefPack 10FB decompression.

Correction 2026-09-30: FIVE-byte header = magic + 24-bit decoded size.
The former six-byte/two-checksum interpretation was incorrect.
Encoder/rebuilder: ../format_lab/fifa_formats.py (separate output only).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'format_lab'))
from fifa_formats import MAX_OUTPUT, identify, refpack_decode, unpack_big_bytes


def parse_big4(path: Path) -> dict:
    if path.stat().st_size > MAX_OUTPUT:
        raise ValueError('MUSE inspection input exceeds 64 MiB')
    data = path.read_bytes()
    if data[:4] != b"BIG4":
        raise ValueError("not a BIG4 container")
    # Validate directory and bounds before compatibility metadata below.
    unpack_big_bytes(data)
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
            entry["10fb"] = {
                "header_hex": payload[:5].hex(" "),
                "header_size": 5,
                "codec": "RefPack-10FB",
                "decoded_size_declared": int.from_bytes(payload[2:5], "big"),
            }
            try:
                body = refpack_decode(payload)
                entry['10fb'].update(decode_ok=True, decoded_size=len(body),
                    decoded_sha256=hashlib.sha256(body).hexdigest(),
                    decoded_format=identify(body[:8192], name),
                    decoded_prefix=body[:120].decode('utf-8', 'replace'))
                if name.lower().endswith('.xml'):
                    ET.fromstring(body)
                    entry['10fb']['xml_parsed'] = True
            except (ValueError, ET.ParseError) as error:
                entry['10fb']['error'] = str(error)
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
