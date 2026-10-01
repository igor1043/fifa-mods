"""Bounded, offline FIFA asset tools. No game loading, RAM access or installation.

BIG directory: OpenSAGE/Docs file-formats/big/index.rst.
RefPack token specification: SSXModding/bigfile src/bigfile/RefPack.cpp.
Implementation below is independent; supports the observed 10 FB / 24-bit form.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zlib

MAX_OUTPUT = 64 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode_text(data):
    """Strict Unicode first; explicitly labelled legacy candidate otherwise."""
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16'), 'utf-16-bom'
    try:
        text = data.decode('utf-8-sig')
        encoding = 'utf-8'
    except UnicodeDecodeError:
        text = data.decode('cp1252')
        encoding = 'cp1252-candidate'
    controls = sum(ord(c) < 32 and c not in '\t\r\n\f' for c in text)
    if controls > max(0, len(text) // 100):
        raise ValueError('binary controls in purported text')
    return text, encoding


def identify(data, name=''):
    signatures = [
        (b'BIG4', 'BIG4'), (b'BIGF', 'BIGF'), (b'CRWD', 'CRWD'),
        (b'chunkzip', 'chunkzip'), (b'chunlzma', 'chunlzma'), (b'ESIA', 'ESIA'),
        (b'EASF', 'EASF'), (b'Apt1', 'APT_CONST'),
        (b'Apt Data:', 'APT'), (b'APT_CONST', 'APT_CONST'),
        (b'Apt Const', 'APT_CONST'), (b'\x1bLua', 'Lua-bytecode'),
        (b'DDS ', 'DDS'), (b'\x89PNG\r\n\x1a\n', 'PNG'),
        (b'\xff\xd8\xff', 'JPEG'), (b'GIF87a', 'GIF'), (b'GIF89a', 'GIF'),
        (b'PK\x03\x04', 'ZIP'), (b'PK\x05\x06', 'ZIP'),
        (b'Rar!\x1a\x07', 'RAR'), (b'7z\xbc\xaf\x27\x1c', '7Z'),
        (b'\x1f\x8b', 'GZIP'), (b'\xfd7zXZ\0', 'XZ'),
        (b'BZh', 'BZIP2'), (b'OggS', 'OGG'), (b'RIFF', 'RIFF'),
        (b'BIK', 'BIK'), (b'KB2', 'BIK2'), (b'RX3', 'RX3'),
        (b'MZ', 'PE-candidate'), (b'DB\0', 'T3DB'),
        (b'FSB', 'FSB'), (b'\x28\xb5\x2f\xfd', 'ZSTD'),
        (b'ID3', 'ID3-audio-candidate'), (b'OTTO', 'OpenType'),
        (b'\x00\x01\x00\x00', 'TrueType-candidate'),
        (b'DKIF', 'IVF-video'), (b'\x1a\x45\xdf\xa3', 'EBML'),
    ]
    if not data:
        return 'EMPTY'
    for magic, kind in signatures:
        if data.startswith(magic):
            return kind
    if len(data) >= 2 and data[1] == 0xfb and data[0] in (0x10, 0x11, 0x50, 0x90):
        return 'RefPack-10FB' if data[0] == 0x10 else 'RefPack-variant'
    if len(data) > 2 and data[0] == 0x78 and ((data[0] << 8) + data[1]) % 31 == 0:
        return 'ZLIB-candidate'
    if (len(data) >= 4 and data[0] == 255 and data[1] & 0xe0 == 0xe0
            and (data[1] >> 3) & 3 != 1 and (data[1] >> 1) & 3 != 0
            and data[2] >> 4 not in (0, 15) and (data[2] >> 2) & 3 != 3):
        return 'MPEG-audio-candidate'
    try:
        text, enc = decode_text(data)
        if len(text) >= 4:
            return 'TEXT-' + enc
    except (ValueError, UnicodeError):
        pass
    return 'UNKNOWN'


def big_directory(stream, size):
    stream.seek(0)
    header = stream.read(16)
    if len(header) != 16 or header[:4] not in (b'BIG4', b'BIGF'):
        raise ValueError('not BIG4/BIGF')
    le, be = int.from_bytes(header[4:8], 'little'), int.from_bytes(header[4:8], 'big')
    endian = 'little' if le == size else 'big' if be == size else 'unmatched'
    count, directory_end = struct.unpack_from('>II', header, 8)
    if count > 2_000_000 or not 16 <= directory_end <= min(size, MAX_OUTPUT):
        raise ValueError('implausible BIG directory count/size')
    directory = header + stream.read(directory_end - 16)
    if len(directory) != directory_end:
        raise ValueError('truncated BIG directory')
    cursor = 16
    entries = []
    for index in range(count):
        if cursor + 9 > len(directory):
            raise ValueError(f'truncated directory entry {index}')
        offset, length = struct.unpack_from('>II', directory, cursor)
        end = directory.find(b'\0', cursor + 8)
        if end == -1 or end - cursor > 65544:
            raise ValueError(f'invalid entry name {index}')
        raw_name = directory[cursor + 8:end]
        cursor = end + 1
        if offset + length > size or (length and offset < directory_end):
            raise ValueError(f'entry {index} outside data section')
        entries.append({'index': index, 'name': raw_name.decode('latin1'),
                        'offset': offset, 'size': length})
    return {'magic': header[:4].decode(), 'size': size, 'size_endian': endian,
            'size_field_le': le, 'size_field_be': be,
            'count': count, 'directory_end': directory_end, 'names_end': cursor,
            'directory_trailer_hex': directory[cursor:].hex(), 'entries': entries}


def unpack_big_bytes(data):
    info = big_directory(io.BytesIO(data), len(data))
    return info, [(e['name'], data[e['offset']:e['offset'] + e['size']]) for e in info['entries']]


def build_big(entries, magic='BIG4', alignment=64, trailer=b''):
    """Canonical standalone BIG. Preserves order/duplicate names, not original offsets/BH."""
    if magic not in ('BIG4', 'BIGF') or alignment < 1 or alignment & (alignment - 1):
        raise ValueError('invalid magic or alignment')
    names = [name.encode('latin1') for name, payload in entries]
    if any(b'\0' in name for name in names):
        raise ValueError('NUL in entry name')
    directory_end = 16 + sum(9 + len(name) for name in names) + len(trailer)
    cursor = (directory_end + alignment - 1) & ~(alignment - 1)
    locations = []
    for _, payload in entries:
        locations.append(cursor)
        cursor = (cursor + len(payload) + alignment - 1) & ~(alignment - 1)
    if cursor >= 2**32:
        raise ValueError('BIG exceeds 32-bit format')
    output = bytearray(cursor)
    output[:16] = magic.encode() + struct.pack('<I', cursor) + struct.pack('>II', len(entries), directory_end)
    pos = 16
    for index, (name, payload) in enumerate(entries):
        entry = struct.pack('>II', locations[index], len(payload)) + names[index] + b'\0'
        output[pos:pos + len(entry)] = entry
        pos += len(entry)
        output[locations[index]:locations[index] + len(payload)] = payload
    output[pos:pos + len(trailer)] = trailer
    return bytes(output)


def refpack_decode(data, limit=MAX_OUTPUT):
    if len(data) < 6 or data[:2] != b'\x10\xfb':
        raise ValueError('only RefPack 10 FB / 24-bit size is supported')
    expected = int.from_bytes(data[2:5], 'big')
    if expected > limit:
        raise ValueError('RefPack exceeds output limit')
    pos = 5
    output = bytearray()
    while True:
        if pos >= len(data):
            raise ValueError('missing RefPack terminal command')
        command = data[pos]
        pos += 1
        copy = 0
        distance = 0
        needed = 1 if command < 0x80 else 2 if command < 0xc0 else 3 if command < 0xe0 else 0
        if pos + needed > len(data):
            raise ValueError('truncated RefPack command')
        if command < 0x80:
            literals = command & 3
            copy = ((command >> 2) & 7) + 3
            distance = ((command & 0x60) << 3) + data[pos] + 1
        elif command < 0xc0:
            literals = data[pos] >> 6
            copy = (command & 0x3f) + 4
            distance = ((data[pos] & 0x3f) << 8) + data[pos + 1] + 1
        elif command < 0xe0:
            literals = command & 3
            copy = ((command & 0x0c) << 6) + data[pos + 2] + 5
            distance = ((command & 0x10) << 12) + (data[pos] << 8) + data[pos + 1] + 1
        else:
            literals = ((command & 0x1f) + 1) * 4 if command < 0xfc else command & 3
        pos += needed
        if pos + literals > len(data) or len(output) + literals + copy > expected:
            raise ValueError('RefPack input/output bounds exceeded')
        output.extend(data[pos:pos + literals])
        pos += literals
        if copy:
            if distance > len(output):
                raise ValueError('RefPack backreference precedes output')
            for _ in range(copy):
                output.append(output[-distance])
        if command >= 0xfc:
            break
    if len(output) != expected:
        raise ValueError(f'RefPack decoded {len(output)} != declared {expected}')
    if pos != len(data):
        raise ValueError(f'{len(data) - pos} trailing bytes after RefPack stream')
    return bytes(output)


def refpack_encode(data):
    """Greedy LZ encoder; valid output, not EA-optimal or byte-identical compression."""
    if len(data) >= 2**24:
        raise ValueError('10FB 24-bit input limit exceeded')
    output = bytearray(b'\x10\xfb' + len(data).to_bytes(3, 'big'))
    buckets = {}
    pending = bytearray()

    def key(pos):
        return (data[pos] * 251 + data[pos + 1] * 31 + data[pos + 2]) & 65535

    def remember(pos):
        if pos + 2 < len(data):
            buckets.setdefault(key(pos), collections.deque(maxlen=12)).append(pos)

    def flush_literals():
        while len(pending) >= 4:
            length = min(112, len(pending) & ~3)
            output.append(0xe0 + length // 4 - 1)
            output.extend(pending[:length])
            del pending[:length]

    pos = 0
    while pos < len(data):
        best_length, best_distance = 0, 0
        if pos + 2 < len(data):
            for previous in reversed(buckets.get(key(pos), ())):
                distance = pos - previous
                if distance > 131072:
                    continue
                length = 0
                maximum = min(1028, len(data) - pos)
                while length < maximum and data[previous + length] == data[pos + length]:
                    length += 1
                minimum = 3 if distance <= 1024 else 4 if distance <= 16384 else 5
                if length >= minimum and length > best_length:
                    best_length, best_distance = length, distance
        if not best_length:
            pending.append(data[pos])
            remember(pos)
            pos += 1
            if len(pending) >= 112:
                flush_literals()
            continue
        flush_literals()
        tail = len(pending)
        distance = best_distance - 1
        if best_length <= 10 and best_distance <= 1024:
            output.extend((((distance >> 8) << 5) | ((best_length - 3) << 2) | tail, distance & 255))
        elif best_length <= 67 and best_distance <= 16384:
            output.extend((0x80 | (best_length - 4), (tail << 6) | (distance >> 8), distance & 255))
        else:
            # A 3/4-byte match can only reach here with an invalid distance, excluded above.
            output.extend((0xc0 | ((distance >> 16) << 4) | (((best_length - 5) >> 8) << 2) | tail,
                           (distance >> 8) & 255, distance & 255, (best_length - 5) & 255))
        output.extend(pending)
        pending.clear()
        for i in range(pos, pos + best_length):
            remember(i)
        pos += best_length
    flush_literals()
    output.append(0xfc | len(pending))
    output.extend(pending)
    return bytes(output)


def chunkzip_decode_single(data, limit=MAX_OUTPUT):
    """Strict observed version-2/single-block/16-byte descriptor dialect only.

    Multi-block/variable-descriptor retail dialects are deliberately rejected.
    Fields are checked against the observed skillmoveai fixture, not guessed
    offsets in arbitrary files. DEFLATE has its own independent zlib validator.
    """
    if len(data) < 48 or data[:8] != b'chunkzip':
        raise ValueError('not observed chunkzip dialect')
    version, size, capacity, count, descriptor, r0, r1, r2, stored, flag = struct.unpack_from('>10I', data, 8)
    if (version, count, descriptor, r0, r1, r2, flag) != (2, 1, 16, 0, 0, 0, 1):
        raise ValueError('unsupported chunkzip dialect; only observed single-block descriptor supported')
    if not size <= min(capacity, limit) or len(data) != 48 + stored:
        raise ValueError('chunkzip declared sizes/bounds invalid')
    decoder = zlib.decompressobj(-15)
    result = decoder.decompress(data[48:], size + 1)
    if len(result) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('chunkzip DEFLATE length/termination invalid')
    return result


def chunkzip_encode_single(data):
    """Experimental symmetric writer for the observed single-block dialect."""
    if len(data) > 0x2d000:
        raise ValueError('single-block writer limited to observed 0x2d000 capacity')
    compressor = zlib.compressobj(level=9, wbits=-15)
    payload = compressor.compress(data) + compressor.flush()
    return b'chunkzip' + struct.pack('>10I', 2, len(data), 0x2d000, 1, 16, 0, 0, 0, len(payload), 1) + payload


def outside_input(input_path, output_path, game_root):
    source, dest, game = input_path.resolve(), output_path.resolve(), game_root.resolve()
    if source == dest or dest == game or game in dest.parents:
        raise ValueError('output must be separate and outside the installed game')
    if dest.exists():
        raise ValueError('output already exists; select a new path')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, default=Path(r'U:\fifa 16'))
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'decode', 'encode', 'unpack', 'pack', 'decode-chunkzip', 'encode-chunkzip'):
        p = sub.add_parser(command)
        p.add_argument('input', type=Path)
        if command != 'inspect':
            p.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'inspect':
        with args.input.open('rb') as stream:
            prefix = stream.read(8192)
            result = {'format': identify(prefix, args.input.name), 'size': args.input.stat().st_size}
            if result['format'] in ('BIG4', 'BIGF'):
                result.update(big_directory(stream, result['size']))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    outside_input(args.input, args.output, args.game_root)
    if args.command == 'pack':
        manifest = json.loads((args.input / 'manifest.json').read_text(encoding='utf-8'))
        entries = []
        for e in manifest['entries']:
            path = (args.input / e['file']).resolve()
            if args.input.resolve() not in path.parents:
                raise ValueError('manifest path escapes extraction directory')
            entries.append((e['name'], path.read_bytes()))
        result = build_big(entries, manifest['magic'], trailer=bytes.fromhex(manifest.get('directory_trailer_hex', '')))
        if unpack_big_bytes(result)[1] != entries:
            raise ValueError('BIG payload validation failed')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as stream:
            stream.write(result)
    else:
        if args.input.stat().st_size > MAX_OUTPUT:
            raise ValueError('CLI extraction/codec input exceeds 64 MiB; inventory supports larger archives')
        data = args.input.read_bytes()
        if args.command == 'unpack':
            info, entries = unpack_big_bytes(data)
            args.output.mkdir(parents=True)
            for i, (name, payload) in enumerate(entries):
                # Numeric files preserve duplicate/unsafe archive names as inert metadata.
                filename = f'{i:06d}.payload'
                (args.output / filename).write_bytes(payload)
                info['entries'][i].update(file=filename, sha256=sha(payload), format=identify(payload[:8192], name))
            (args.output / 'manifest.json').write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding='utf-8')
        else:
            codecs = {'decode': refpack_decode, 'encode': refpack_encode,
                      'decode-chunkzip': chunkzip_decode_single, 'encode-chunkzip': chunkzip_encode_single}
            result = codecs[args.command](data)
            if args.command == 'encode' and refpack_decode(result) != data:
                raise ValueError('RefPack self-check failed')
            if args.command == 'encode-chunkzip' and chunkzip_decode_single(result) != data:
                raise ValueError('chunkzip self-check failed')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('xb') as stream:
                stream.write(result)
    print(json.dumps({'output': str(args.output), 'installed': False, 'game_tested': False}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
