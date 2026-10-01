"""Inventory every regular file and nested uncompressed BIG directory (read-only).

Recognition is not decoding. Embedded streams inside opaque formats/ZIP/RAR are
reported as unexpanded. Raw BIG nesting is bounded and every limit is reported.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from fifa_formats import big_directory, identify, sha


class Slice:
    def __init__(self, stream, start, size):
        self.stream, self.start, self.size, self.pos = stream, start, size, 0
    def seek(self, pos):
        if not 0 <= pos <= self.size:
            raise ValueError('slice seek out of bounds')
        self.pos = pos
    def read(self, count):
        count = min(count, self.size - self.pos)
        self.stream.seek(self.start + self.pos)
        data = self.stream.read(count)
        self.pos += len(data)
        return data


def walk(root, errors):
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        # Junctions are recorded, not followed out of the requested tree.
                        if entry.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(entry.path)):
                            errors.append({'path': entry.path, 'reason': 'link/junction not followed'})
                        elif entry.is_dir(follow_symlinks=False):
                            pending.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            yield Path(entry.path)
                    except OSError as e:
                        errors.append({'path': entry.path, 'reason': str(e)})
        except OSError as e:
            errors.append({'path': str(current), 'reason': str(e)})


def inspect_file(path, root):
    rows = []
    relative = str(path.relative_to(root))
    try:
        stat = path.stat()
        with path.open('rb') as stream:
            def visit(start, size, names, depth):
                view = Slice(stream, start, size)
                prefix = view.read(min(1024, size))
                name = names[-1]['name'] if names else path.name
                row = {'path': relative, 'members': names, 'offset': start, 'size': size,
                       'mtime_ns': stat.st_mtime_ns, 'format': identify(prefix, name),
                       'extension': Path(name).suffix.lower(), 'header_hex': prefix[:16].hex(),
                       'header_sha256': sha(prefix), 'evidence': 'signature_only', 'full_decode': False}
                rows.append(row)
                if row['format'] in ('BIG4', 'BIGF'):
                    if depth >= 4:
                        row['unexpanded_reason'] = 'BIG depth limit 4'
                        return
                    try:
                        info = big_directory(view, size)
                        row.update(evidence='directory_validated', entry_count=info['count'],
                                   size_endian=info['size_endian'])
                        for e in info['entries']:
                            visit(start + e['offset'], e['size'], names + [{'index': e['index'], 'name': e['name']}], depth + 1)
                    except (ValueError, OSError) as e:
                        row['parse_error'] = str(e)
                elif row['format'] in ('ZIP', 'RAR', '7Z', 'RefPack-10FB', 'RefPack-variant', 'chunkzip'):
                    row['unexpanded_reason'] = 'payload decode is a separate bounded validation step'
            visit(0, stat.st_size, [], 0)
        after = path.stat()
        if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            rows[0]['read_warning'] = 'source changed during inventory'
    except (OSError, ValueError) as e:
        rows.append({'path': relative, 'members': [], 'read_error': str(e), 'format': 'READ_ERROR'})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    root, out = a.root.resolve(), a.output.resolve()
    if out == root or root in out.parents or out.exists():
        raise ValueError('choose a new output directory outside the game')
    out.mkdir(parents=True)
    errors = []
    files = sorted(walk(root, errors))
    physical, embedded, unknown = Counter(), Counter(), Counter()
    samples = defaultdict(list)
    failures, bytes_total, parsed, nested_limits = [], 0, 0, 0
    with (out / 'files.jsonl').open('w', encoding='utf-8') as report, ThreadPoolExecutor(max_workers=a.workers) as pool:
        for number, rows in enumerate(pool.map(lambda f: inspect_file(f, root), files), 1):
            for row in rows:
                report.write(json.dumps(row, ensure_ascii=False) + '\n')
                kind = row['format']
                (embedded if row['members'] else physical)[kind] += 1
                if not row['members']:
                    bytes_total += row.get('size', 0)
                if kind == 'UNKNOWN':
                    unknown[row.get('extension') or '(no extension)'] += 1
                if row.get('evidence') == 'directory_validated':
                    parsed += 1
                if row.get('unexpanded_reason') == 'BIG depth limit 4':
                    nested_limits += 1
                if any(k in row for k in ('parse_error', 'read_error', 'read_warning')):
                    failures.append(row)
                if len(samples[kind]) < 12:
                    samples[kind].append(row)
            if number % 2000 == 0:
                print(json.dumps({'progress': number, 'total': len(files)}), flush=True)
    summary = {'time_utc': datetime.now(timezone.utc).isoformat(), 'root': str(root),
               'physical_files': len(files), 'physical_bytes': bytes_total,
               'physical_formats': dict(physical.most_common()), 'embedded_formats': dict(embedded.most_common()),
               'embedded_entries': sum(embedded.values()), 'big_directories_validated': parsed,
               'nested_depth_limits': nested_limits, 'unknown_extensions': dict(unknown.most_common()),
               'filesystem_errors': errors, 'file_errors': failures,
               'scope': 'all regular files; nested raw BIG to depth 4; signatures do not prove full decode',
               'game_started': False, 'ram_accessed': False, 'game_files_written': False}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    (out / 'samples.json').write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('file_errors', 'filesystem_errors')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
