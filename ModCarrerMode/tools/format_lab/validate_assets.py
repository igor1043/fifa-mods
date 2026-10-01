"""Reproducible offline checks against real assets; creates a NEW Dev run only.

No game execution, writes, RAM access or BH regeneration. All exceptions are
reported as failed/unsupported samples, never silently counted as successes.
"""
import argparse
from collections import Counter, defaultdict
import io
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from fifa_formats import (MAX_OUTPUT, build_big, identify, outside_input,
                          refpack_decode, refpack_encode, sha, unpack_big_bytes)


def read_member(root, row):
    if row['size'] > MAX_OUTPUT:
        raise ValueError('sample exceeds 64 MiB limit')
    with (root / row['path']).open('rb') as stream:
        stream.seek(row['offset'])
        data = stream.read(row['size'])
    if len(data) != row['size']:
        raise ValueError('truncated sample')
    if sha(data[:1024]) != row['header_sha256']:
        raise ValueError('header changed since inventory')
    return data


def check_muse(root, out):
    path = root / 'data/bcdata/muse/musedata-match.big'
    data = path.read_bytes()
    info, entries = unpack_big_bytes(data)
    results, decoded = [], []
    for index, (name, payload) in enumerate(entries):
        row = {'index': index, 'name': name, 'stored_size': len(payload)}
        try:
            plain = refpack_decode(payload)
            row.update(decoded_size=len(plain), decoded_sha256=sha(plain),
                       decoded_format=identify(plain[:8192], name), decode_ok=True)
            if name.lower().endswith('.xml') or plain.lstrip().startswith(b'<?xml'):
                ET.fromstring(plain)
                row['xml_parsed'] = True
            decoded.append((index, plain))
        except (ValueError, ET.ParseError) as error:
            row['error'] = str(error)
        results.append(row)
    (out / 'muse_entries.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    trailer = bytes.fromhex(info['directory_trailer_hex'])
    rebuilt = build_big(entries, info['magic'], trailer=trailer)
    if unpack_big_bytes(rebuilt)[1] != entries:
        raise ValueError('MUSE rebuild failed payload/order validation')
    (out / 'muse_roundtrip.big').write_bytes(rebuilt)
    selected = sorted(decoded, key=lambda item: len(item[1]))
    indexes = sorted(set([0, len(selected)//4, len(selected)//2, 3*len(selected)//4, len(selected)-1])) if selected else []
    compression = []
    for i in indexes:
        index, plain = selected[i]
        packed = refpack_encode(plain)
        if refpack_decode(packed) != plain:
            raise ValueError(f'MUSE encoder failed entry {index}')
        (out / f'muse_{index:04d}_plain.payload').write_bytes(plain)
        (out / f'muse_{index:04d}_encoded.refpack').write_bytes(packed)
        compression.append({'index': index, 'plain_size': len(plain), 'new_size': len(packed),
                            'plain_sha256': sha(plain), 'roundtrip_equal': True})
    edited = None
    for index, plain in decoded:
        if not results[index].get('xml_parsed'):
            continue
        # Harmless XML comment in a disposable COPY, not a requested game change.
        altered = plain + b'\n<!-- offline-format-lab-test; NOT INSTALLED -->\n'
        ET.fromstring(altered)
        changed_entries = list(entries)
        changed_entries[index] = (entries[index][0], refpack_encode(altered))
        candidate = build_big(changed_entries, info['magic'], trailer=trailer)
        recovered = unpack_big_bytes(candidate)[1]
        changes = [i for i in range(len(entries)) if recovered[i] != entries[i]]
        if changes != [index] or refpack_decode(recovered[index][1]) != altered:
            raise ValueError('MUSE isolated edit validation failed')
        (out / 'muse_one_comment_EXPERIMENTAL.big').write_bytes(candidate)
        edited = {'changed_entries': changes, 'decoded_xml_parsed': True,
                  'other_entries_identical': True, 'installed': False}
        break
    unchanged = sha(path.read_bytes()) == sha(data)
    if not unchanged:
        raise ValueError('source MUSE changed during validation')
    return {'source': str(path), 'source_sha256': sha(data), 'source_unchanged': unchanged,
            'entries': len(entries), 'decoded': sum(r.get('decode_ok', False) for r in results),
            'xml_parsed': sum(r.get('xml_parsed', False) for r in results),
            'errors': [r for r in results if 'error' in r],
            'preserved_names_order_payloads': True, 'opaque_trailer_preserved_hex': trailer.hex(),
            'reencoded_samples': compression, 'isolated_edit': edited,
            'game_acceptance_tested': False, 'bh_regenerated': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('inventory', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    outside_input(a.inventory, a.output, a.root)
    a.output.mkdir(parents=True)
    result = {'muse': check_muse(a.root, a.output)}
    image_samples, refpacks, unknowns, examples = defaultdict(list), [], Counter(), {}
    seq, unusual = [], []
    with (a.inventory / 'files.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            kind = row['format']
            if kind in ('PNG', 'JPEG', 'DDS') and len(image_samples[kind]) < 3:
                image_samples[kind].append(row)
            if kind == 'RefPack-10FB':
                refpacks.append(row)
            if kind == 'UNKNOWN':
                key = (row['header_hex'][:16], row.get('extension', ''))
                unknowns[key] += 1
                examples.setdefault(key, row)
            if row.get('extension') == '.seq' or 'skillmoveai' in row['path'].lower() or any('skillmoveai' in x['name'].lower() for x in row['members']):
                seq.append(row)
            if row.get('parse_error'):
                unusual.append(row)
    from PIL import Image
    images = []
    for kind, samples in image_samples.items():
        for row in samples:
            test = {'path': row['path'], 'members': row['members'], 'format': kind}
            try:
                data = read_member(a.root, row)
                with Image.open(io.BytesIO(data)) as image:
                    image.load()
                    test.update(decoded=True, dimensions=list(image.size), mode=image.mode,
                                pixel_sha256=sha(image.tobytes()))
                test['source_unchanged'] = sha(read_member(a.root, row)) == sha(data)
            except Exception as error:
                test.update(decoded=False, error=str(error))
            images.append(test)
    compressed = []
    for row in refpacks:
        test = {'path': row['path'], 'members': row['members'], 'stored_size': row['size']}
        try:
            data = read_member(a.root, row)
            plain = refpack_decode(data)
            test.update(decoded=True, decoded_size=len(plain), decoded_sha256=sha(plain),
                        decoded_format=identify(plain[:8192]))
        except Exception as error:
            test.update(decoded=False, error=str(error))
        compressed.append(test)
    result.update(images=images, refpack_streams=compressed,
                  unknown_clusters=[{'header_prefix': key[0], 'extension': key[1], 'count': n,
                                     'example': examples[key]} for key, n in unknowns.most_common(100)],
                  sequence_candidates=seq, big_errors=unusual,
                  game_files_written=False, game_started=False, ram_accessed=False)
    (a.output / 'validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'muse': result['muse'], 'images_ok': sum(r.get('decoded',False) for r in images),
                      'refpack_ok': sum(r.get('decoded',False) for r in compressed),
                      'refpack_total':len(compressed), 'sequence_candidates':len(seq)}, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
