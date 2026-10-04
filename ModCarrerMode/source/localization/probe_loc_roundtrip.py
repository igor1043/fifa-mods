"""Read-only LOC audit; editor round-trip outputs must go to an explicit scratch folder.

Run with the 32-bit Python used by FifaLibrary16. Source databases are never saved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loc_db import LocDb


def library(dll: Path, bridge: Path):
    runpy.run_path(str(bridge), run_name="loc_bridge")["_prefer_bundled_site_packages"]()
    sys.path.insert(0, str(dll.parent))
    import clr
    clr.AddReference(str(dll))
    from FifaLibrary import DbFile
    return DbFile


def snapshot(db):
    table = db.GetTable("LanguageStrings")
    rows = []
    for i in range(table.NValidRecords):
        r = table.Records[i]
        rows.append((int(r.GetIntField("hashid")),
                     str(r.GetStringField("stringid")),
                     str(r.GetStringField("sourcetext"))))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", type=Path, required=True)
    ap.add_argument("--bridge", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("paths", type=Path, nargs="+")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    DbFile = library(args.dll, args.bridge)
    for index, path in enumerate(args.paths):
        original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        meta = path.with_name(path.stem + "-meta.xml")
        working = args.output / f"{index}-{path.stem}-input.db"
        if working.exists():
            raise ValueError(f"Refusing to overwrite {working}")
        shutil.copyfile(path, working)
        db = DbFile(str(working), str(meta))
        if not db.Load():
            raise ValueError(f"Cannot load {path}")
        before = snapshot(db)
        binary = LocDb.read(path.read_bytes())
        if binary.rows != before:
            raise ValueError("Independent UTF-8/Huffman reader differs from FifaLibrary")
        table = db.GetTable("LanguageStrings")
        fields = table.TableDescriptor.FieldDescriptors
        schema = [{str(p.Name): str(p.GetValue(fields[i], None))
                   for p in fields[i].GetType().GetProperties()}
                  for i in range(table.TableDescriptor.NFields)]
        passes = []
        for number in range(1, 3):
            out = args.output / f"{index}-{path.stem}-save-{number}.db"
            if out.exists():
                raise ValueError(f"Refusing to overwrite {out}")
            shutil.copyfile(working, out)
            db = DbFile(str(out), str(meta))
            if not db.Load() or snapshot(db) != before:
                raise ValueError("Scratch input differs before save")
            if not db.SaveDb():
                raise ValueError(f"Cannot save scratch {out}")
            reloaded = DbFile(str(out), str(meta))
            if not reloaded.Load():
                raise ValueError(f"Cannot reopen scratch {out}")
            after = snapshot(reloaded)
            changed = [(a, b) for a, b in zip(before, after) if a != b]
            raw = LocDb.read(out.read_bytes())
            independent_matches = raw.rows == after
            passes.append({"pass": number, "rows": len(after),
                           "changed": len(changed), "examples": changed[:8],
                           "independent_reader_matches": independent_matches,
                           "max_code_bits": raw.tree.max_bits,
                           "editor_crc_valid": True,
                           "replacement_rows": sum("\ufffd" in r[2] for r in after),
                           "sha256": hashlib.sha256(out.read_bytes()).hexdigest()})
            if changed or len(after) != len(before) or not independent_matches:
                raise ValueError(f"Editor save changed translations in {out}")
            raw.tree.require_editor_safe()
            db = reloaded
            working = out
        if hashlib.sha256(path.read_bytes()).hexdigest() != original_hash:
            raise AssertionError("Source changed")
        report = {"source": str(path), "sha256": original_hash, "rows": len(before),
                  "schema": schema, "passes": passes,
                  "custom": [r for r in before if r[1].startswith("FIFA_MODS")],
                  "sentinels": [r for r in before if r[1] in
                                {"TeamName_112705", "CM_Competition_upper", "PressStartPC"}]}
        (args.output / f"{index}-{path.stem}-report.json").write_text(
            json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items()
                          if k not in {"schema", "custom"}}, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
