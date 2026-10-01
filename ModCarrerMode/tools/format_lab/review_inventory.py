"""Refine an existing inventory using stored signatures; no repeated game scan.

Only UNKNOWN rows are reconsidered and text guesses from 16 bytes are rejected.
The result is a capability map, not a claim that every payload has been decoded.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from fifa_formats import identify, outside_input


def capability(kind):
    if kind in ('BIG4', 'BIGF'):
        return 'directory/extract/rebuild implemented; BH not regenerated; engine untested'
    if kind == 'RefPack-10FB':
        return 'decode/encode implemented; see separate asset validation for actual stream coverage'
    if kind in ('PNG', 'JPEG', 'DDS'):
        return 'Pillow decoder available; 3 samples per format decoded; remaining payloads untested'
    if kind.startswith('TEXT-'):
        return 'text prefix classification only; whole-file decoding not validated for game corpus'
    if kind in ('T3DB', 'CRWD', 'APT', 'APT_CONST', 'RX3', 'PE-candidate', 'Lua-bytecode'):
        return 'known family; existing/historical partial readers; no generic full roundtrip here'
    if kind in ('ZIP', 'RAR', '7Z', 'ID3-audio-candidate', 'MPEG-audio-candidate', 'OpenType', 'TrueType-candidate', 'IVF-video', 'EBML'):
        return 'standard-family candidate; full decoding not tested in this audit'
    if kind == 'chunkzip':
        return 'strict single-block decoder/encoder implemented; other dialects unsupported here'
    if kind == 'EASF':
        return 'historical decode/rebuild reports; old codec not located in current scoped tool directories'
    if kind == 'chunlzma':
        return 'wrapper signature only; no decoder implemented here'
    if kind == 'EMPTY':
        return 'no payload; may be intentional placeholder'
    return 'unmapped/unsupported by this laboratory; not proof of encryption or impossibility'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inventory', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--game-root', type=Path, default=Path(r'U:\fifa 16'))
    a = p.parse_args()
    outside_input(a.inventory, a.output, a.game_root)
    a.output.mkdir(parents=True)
    counts = {'physical': Counter(), 'embedded': Counter()}
    unknown, examples = Counter(), {}
    groups, partitions = defaultdict(list), Counter()
    changed = 0
    with (a.output/'reclassified.jsonl').open('w', encoding='utf-8') as delta, (a.inventory/'files.jsonl').open(encoding='utf-8') as source:
        for line in source:
            row = json.loads(line)
            kind = row['format']
            if kind == 'UNKNOWN':
                candidate = identify(bytes.fromhex(row['header_hex']))
                if candidate != 'UNKNOWN' and not candidate.startswith('TEXT-'):
                    kind = candidate
                    row.update(original_format='UNKNOWN', format=kind, refinement='stored 16-byte signature; not a full decode')
                    delta.write(json.dumps(row,ensure_ascii=False)+'\n')
                    changed += 1
            location = 'embedded' if row['members'] else 'physical'
            counts[location][kind] += 1
            if location == 'physical':
                partitions[row['path'].split('\\')[0] if '\\' in row['path'] else '(root)'] += 1
            if kind == 'UNKNOWN':
                key = (location, row.get('extension') or '(no extension)', row['header_hex'][:16])
                unknown[key] += 1
                examples.setdefault(key, row)
            if len(groups[kind]) < 5:
                groups[kind].append(row)
    result = {'physical_formats':dict(counts['physical'].most_common()),
              'embedded_formats':dict(counts['embedded'].most_common()),
              'reclassified':changed, 'physical_partitions':dict(partitions.most_common()),
              'capabilities':{kind:capability(kind) for kind in groups},
              'unknown_clusters':[{'location':k[0], 'extension':k[1], 'prefix':k[2], 'count':n,
                                   'example':examples[k]} for k,n in unknown.most_common(100)],
              'samples':dict(groups), 'mode':'stored-header refinement; original inventory retained'}
    (a.output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('physical_formats','embedded_formats','reclassified','physical_partitions')},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
