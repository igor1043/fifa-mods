"""Stage LOC DBs with editor-compatible original Huffman trees.

No in-place writes. Install only after probe_loc_roundtrip.py passes using
FifaLibrary16 (the independent editor reader/writer). Future known-ID text
updates use a UTF-8 JSON map; unknown IDs are refused, not silently invented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from loc_db import LocDb, Tree


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(source, output, reference=None, catalog=None, updates=None):
    if source.resolve() == output.resolve() or (reference and reference.resolve() == output.resolve()):
        raise ValueError("Output must be separate from source/reference")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be new/empty")
    paths = sorted(source.glob("*.db"))
    if not paths:
        raise ValueError("No LOC DBs found")
    updates = updates or {}
    unknown_files = set(updates) - {p.name for p in paths}
    if unknown_files:
        raise ValueError(f"Updates target unknown languages: {sorted(unknown_files)}")
    staged, report, trees = [], [], {}
    for path in paths:
        data = path.read_bytes()
        db = LocDb.read(data)
        if reference:
            reference_data = (reference / path.name).read_bytes()
            reference_text_audit = "valid-utf8"
            try:
                baseline = LocDb.read(reference_data)
            except UnicodeDecodeError:
                # A legacy reference may already contain truncated UTF-8 text.
                # Its tree can still be audited independently; never restore
                # those corrupted rows over the current functional mod data.
                baseline = LocDb.read(reference_data, decode_rows=False)
                reference_text_audit = "unavailable-invalid-reference-utf8"
            tree = baseline.tree
            strategy = "original-compatible-tree"
            if tree.max_bits > 16 or not set(db.tree.codes).issubset(tree.codes):
                tree = Tree.balanced(set(db.tree.codes) | set(tree.codes))
                strategy = "deterministic-balanced-tree"
            tree.require_editor_safe()
            trees[path.name] = {"reference_sha256": sha(reference_data),
                                "strategy": strategy,
                                "tree_sha256": sha(tree.raw),
                                "max_code_bits": tree.max_bits, "tree_hex": tree.raw.hex()}
        else:
            entry = catalog[path.name]
            tree = Tree(bytes.fromhex(entry["tree_hex"]))
            if sha(tree.raw) != entry["tree_sha256"] or tree.max_bits != entry["max_code_bits"]:
                raise ValueError("Original tree catalog integrity mismatch")
            trees[path.name] = entry
        rows = []
        changes = updates.get(path.name, {})
        unknown = set(changes) - {key for _, key, _ in db.rows}
        if unknown:
            raise ValueError(f"Refusing unknown translation IDs: {sorted(unknown)}")
        for h, key, text in db.rows:
            rows.append((h, key, changes.get(key, text)))
        corrected = db.serialize(tree, rows)
        reopened = LocDb.read(corrected)
        if reopened.rows != rows or reopened.tree.raw != tree.raw:
            raise ValueError("Independent binary verification failed")
        if reopened.serialize(tree) != corrected:
            raise ValueError("LOC serialization is not stable")
        # Preserve metadata bytes exactly: the reported failure is not XML.
        meta = source / (path.stem + "-meta.xml")
        if not meta.is_file():
            raise ValueError(f"Missing metadata {meta}")
        staged.append((path, corrected, meta))
        item = {"file": path.name, "rows": len(rows), "before_sha256": sha(data),
                "after_sha256": sha(corrected), "before_max_code_bits": db.tree.max_bits,
                "after_max_code_bits": tree.max_bits,
                "rows_changed": sum(a != b for a, b in zip(rows, db.rows)),
                "strategy": trees[path.name].get("strategy"),
                "custom_mod_rows": sum(k.startswith("FIFA_MODS_") for _, k, _ in rows),
                "inherited_replacement_rows": sum("\ufffd" in text for _, _, text in rows),
                "metadata_sha256": sha(meta.read_bytes())}
        if reference:
            item["reference_text_audit"] = reference_text_audit
            before_map = {(h, key): text for h, key, text in baseline.rows}
            after_map = {(h, key): text for h, key, text in rows}
            item["original_rows_missing"] = (len(set(before_map) - set(after_map))
                                             if baseline.rows else None)
            item["original_text_differences"] = [k for h, k in before_map
                if (h, k) in after_map and before_map[h, k] != after_map[h, k]]
        report.append(item)
        print(json.dumps({k: v for k, v in item.items()
                          if k != "original_text_differences"}), flush=True)
    output.mkdir(parents=True, exist_ok=True)
    for path, corrected, meta in staged:
        # Detect a source modification during preparation.
        item = next(r for r in report if r["file"] == path.name)
        if sha(path.read_bytes()) != item["before_sha256"]:
            raise ValueError("Source changed during audit")
        (output / path.name).write_bytes(corrected)
        shutil.copyfile(meta, output / meta.name)
    (output / "repair-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "original-huffman-trees.json").write_text(json.dumps(trees, indent=2), encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--reference-dir", type=Path)
    group.add_argument("--tree-catalog", type=Path)
    ap.add_argument("--updates", type=Path, help="UTF-8 JSON: {language.db: {stringid: text}}")
    args = ap.parse_args()
    catalog = json.loads(args.tree_catalog.read_text(encoding="utf-8")) if args.tree_catalog else None
    updates = json.loads(args.updates.read_text(encoding="utf-8")) if args.updates else None
    prepare(args.source_dir, args.output_dir, args.reference_dir, catalog, updates)


if __name__ == "__main__":
    main()
