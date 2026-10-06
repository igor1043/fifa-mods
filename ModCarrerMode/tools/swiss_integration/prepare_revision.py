"""Prepare the reviewed Swiss additions against the confirmed working V12.

Existing UI archives are compared internally, recorded and never rewritten.
The donor is compiled; native byte descriptors are reconstructed as C tables.
This tool only writes Dev files. Installation is a separate backed-up step.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'format_lab'))
import fifa_formats as formats
import pefile

DONOR_SHA = '8c5b1322638d88075ed57ad466ee934343b4284d70b011aff3f81a78e07a6de9'
BASE_WINMM_SHA = 'b43513ddeab5f9f0904eb76e4cb543596ca35b1aaae3c60ce7993061b7ac1a0e'

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def read_archive(blob):
    wrapper = 'plain'
    if blob.startswith(b'chunkzip'):
        wrapper = 'chunkzip'
        version, size, block_size, count = struct.unpack_from('>4I', blob, 8)
        if version != 2 or not 0 < size <= formats.MAX_OUTPUT or not 0 < count <= 1024:
            raise ValueError('Unsupported chunkzip header')
        decoded, cursor = bytearray(), 32
        for _ in range(count):
            cursor = (cursor + 3) & ~3
            while blob[cursor:cursor+4] == b'\0' * 4:
                cursor += 4
            stored, flag = struct.unpack_from('>II', blob, cursor)
            cursor += 8
            if flag != 1 or not stored or cursor + stored > len(blob):
                raise ValueError('Invalid chunkzip block')
            decoder = zlib.decompressobj(-15)
            decoded.extend(decoder.decompress(blob[cursor:cursor+stored], size-len(decoded)+1))
            if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or len(decoded) > size:
                raise ValueError('Invalid chunkzip stream')
            cursor += stored
        if len(decoded) != size or any(blob[cursor:]):
            raise ValueError('Invalid chunkzip trailer')
        blob = bytes(decoded)
    elif blob.startswith(b'\x10\xfb'):
        wrapper, blob = 'refpack', formats.refpack_decode(blob)
    info, entries = formats.unpack_big_bytes(blob)
    if len(dict(entries)) != len(entries):
        raise ValueError('Duplicate archive names')
    end = max((entry['offset'] + entry['size'] for entry in info['entries']), default=info['directory_end'])
    return dict(entries), {'wrapper': wrapper, 'length': len(blob),
        'size_field_le': info['size_field_le'], 'size_field_be': info['size_field_be'],
        'size_endian': info['size_endian'],
        'directory_trailer_hex': info['directory_trailer_hex'],
        'tail_hex': blob[end:].hex(), 'count': len(entries)}

def assets(delivery, game, repo):
    records, pending = [], []
    for source in sorted((delivery / 'data').rglob('*.big')):
        relative = source.relative_to(delivery)
        incoming = source.read_bytes()
        new, new_meta = read_archive(incoming)
        existing = game / relative
        record = {'path': relative.as_posix(), 'delivery_sha256': sha(incoming)}
        if not existing.exists():
            record.update(action='added', base_sha256=None, output_sha256=sha(incoming))
            pending.append((repo / relative, incoming))
        else:
            original = existing.read_bytes()
            record.update(base_sha256=sha(original), output_sha256=sha(original))
            if original == incoming:
                record['action'] = 'preserved-identical'
            else:
                old, old_meta = read_archive(original)
                changed = []
                for name in sorted(old.keys() | new.keys()):
                    if old.get(name) != new.get(name):
                        before, after = old.get(name), new.get(name)
                        changed.append({'name': name,
                            'before_kind': formats.identify(before) if before is not None else 'ABSENT',
                            'after_kind': formats.identify(after) if after is not None else 'ABSENT',
                            'before_size': len(before) if before is not None else None,
                            'after_size': len(after) if after is not None else None,
                            'before_sha256': sha(before) if before is not None else None,
                            'after_sha256': sha(after) if after is not None else None})
                record.update(action='preserved-original', entries=changed,
                    original_container=old_meta, delivery_container=new_meta,
                    reason='Existing default presentation/style; new mappings use sets 4,5,11,12,13,14. Preserve original APT code, metadata and opaque footer.')
        records.append(record)
    counts = collections.Counter(r['action'] for r in records)
    if counts != {'added': 693, 'preserved-identical': 118, 'preserved-original': 40}:
        raise ValueError(f'Working base changed; review required: {counts}')
    for target, blob in pending:
        if target.exists() and target.read_bytes() != blob:
            raise ValueError(f'Dev addition conflict: {target}')
    for target, blob in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    (repo / 'ModCarrerMode/docs/swiss-assets-manifest.json').write_text(
        json.dumps(records, indent=2) + '\n', encoding='utf-8')
    print(dict(counts))

def byte_tables(delivery, repo):
    raw = (delivery / 'dinput8.dll').read_bytes()
    if sha(raw) != DONOR_SHA:
        raise ValueError('Unreviewed donor DLL')
    image = pefile.PE(data=raw).get_memory_mapped_image()
    groups, manifest = [], []
    for label, table, count, stride, width in [('kit_keys', 0x23040, 49, 24, 8), ('league_capacity', 0x227E0, 3, 32, 6)]:
        rows = []
        for index in range(count):
            offset = table + stride * index
            rva, length = struct.unpack_from('<IB', image, offset)
            if not 0 < length <= width:
                raise ValueError('Invalid byte descriptor')
            before = image[offset+5:offset+5+length]
            after = image[offset+5+width:offset+5+width+length]
            rows.append('    {0x%08X, %d, {%s}, {%s}}' % (rva, length,
                ','.join('0x%02X' % b for b in before), ','.join('0x%02X' % b for b in after)))
            manifest.append({'group': label, 'descriptor_rva': offset, 'rva': rva,
                'length': length, 'before': before.hex(), 'after': after.hex()})
        groups.append('static const SwissBytePatch swiss_%s[] = {\n%s\n};' % (label, ',\n'.join(rows)))
    header = ('/* Generated by prepare_revision.py from pinned Swiss L9.94 descriptors. */\n'
        '#ifndef SWISS_BYTE_PATCHES_H\n#define SWISS_BYTE_PATCHES_H\n'
        'typedef struct SwissBytePatch { DWORD rva; BYTE length; BYTE before[8]; BYTE after[8]; } SwissBytePatch;\n' + '\n'.join(groups) + '\n#endif\n')
    (repo / 'ModCarrerMode/source/career_native/src/host/swiss_byte_patches.h').write_text(header, encoding='ascii')
    (repo / 'ModCarrerMode/docs/swiss-byte-patches.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')

def settings(delivery, repo):
    target = repo / 'dinput8_L9.ini'
    original = target.read_bytes()
    if b'[SwissIntegration]' in original:
        return
    incoming = (delivery / 'dinput8_L9.ini').read_bytes()
    sections = re.split(rb'(?m)(?=^\[)', incoming)
    selected = {'Ligensperre','Trikotschluessel','Kontinentalturniere','Trikotliste',
        'Ligengroesse','Karrierewaechter','Tabellenwaechter','Entlinkschutz','Scoreboards'}
    addition = b'\r\n; Swiss additions reviewed against working V12. Original sections retained.\r\n[SwissIntegration]\r\nAktiv=1\r\n'
    addition += b'\r\n[Speicherbudget]\r\nAktiv=1\r\nKarriere=3600000\r\nTurnier=3500000\r\n'
    for section in sections:
        match = re.match(rb'\[([^]]+)\]', section)
        if match and match[1].decode('ascii') in selected:
            # Keep keys and local comments; donor block documentation stays in its source.
            lines = []
            for line in section.splitlines():
                if line.strip() and not line.lstrip().startswith((b';', b'#')):
                    lines.append(line)
            addition += b'\r\n' + b'\r\n'.join(lines) + b'\r\n'
    if original.count(b'Basis=350000') != 1:
        raise ValueError('Unrecognized original player ID setting')
    target.write_bytes(original.replace(b'Basis=350000', b'Basis=460000') + addition)

def winmm(repo):
    target = repo / 'winmm.dll'
    blob = target.read_bytes()
    original = bytearray(blob)
    struct.pack_into('<I', original, 0xEC60, 7000)
    if sha(original) != BASE_WINMM_SHA:
        raise ValueError('Unreviewed original winmm; refusing replacement')
    if struct.unpack_from('<I', blob, 0xEC60)[0] not in (7000, 16000):
        raise ValueError('Unknown team initialization capacity')
    output = bytearray(blob)
    struct.pack_into('<I', output, 0xEC60, 16000)
    target.write_bytes(output)
    print('winmm: original binary preserved; InitTeams 7000 -> 16000 (2 bytes)')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery', type=Path, required=True)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    if len({p.resolve() for p in (args.delivery,args.game,args.repo)}) != 3:
        raise ValueError('Separate delivery, game and Dev required')
    assets(args.delivery, args.game, args.repo)
    byte_tables(args.delivery, args.repo)
    settings(args.delivery, args.repo)
    winmm(args.repo)

if __name__ == '__main__':
    main()
