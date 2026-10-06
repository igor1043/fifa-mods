"""Raise only SaveLoadPP to at least 24 MiB, preserving other game settings."""
from pathlib import Path
import argparse
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'format_lab'))
import fifa_formats as formats


def literal_origins(blob):
    """Track decoded bytes back to their original RefPack literal positions."""
    origins, cursor = [], 5
    while cursor < len(blob):
        command = blob[cursor]
        cursor += 1
        needed = 1 if command < 0x80 else 2 if command < 0xc0 else 3 if command < 0xe0 else 0
        copy = distance = 0
        if command < 0x80:
            literals = command & 3
            copy = ((command >> 2) & 7) + 3
            distance = ((command & 0x60) << 3) + blob[cursor] + 1
        elif command < 0xc0:
            literals = blob[cursor] >> 6
            copy = (command & 0x3f) + 4
            distance = ((blob[cursor] & 0x3f) << 8) + blob[cursor+1] + 1
        elif command < 0xe0:
            literals = command & 3
            copy = ((command & 0x0c) << 6) + blob[cursor+2] + 5
            distance = ((command & 0x10) << 12) + (blob[cursor] << 8) + blob[cursor+1] + 1
        else:
            literals = ((command & 0x1f) + 1) * 4 if command < 0xfc else command & 3
        cursor += needed
        origins.extend(range(cursor, cursor+literals))
        cursor += literals
        for _ in range(copy):
            origins.append(origins[-distance])
        if command >= 0xfc:
            break
    return origins


def prepare(blob):
    compressed = blob.startswith(b'\x10\xfb')
    plain = formats.refpack_decode(blob) if compressed else blob
    pattern = rb'(?m)^(AddAllocator[ \t]+SaveLoadPP[ \t]+PPMallocMutex[ \t]+\[[ \t]*size=)(\d+)([Mm])([ \t]*\])'
    matches = list(re.finditer(pattern, plain))
    if len(matches) != 1:
        raise ValueError('Expected one SaveLoadPP allocation; unknown memoryfw layout')
    match = matches[0]
    if int(match[2]) >= 24:
        return blob
    result = plain[:match.start(2)] + b'24' + plain[match.end(2):]
    output = None
    if compressed and len(result) == len(plain):
        # Prefer editing the literal token: keep the original compressed stream
        # and all its metadata. Decode the candidate to prove its exact effect.
        origins = literal_origins(blob)
        candidate = bytearray(blob)
        for index, (before, after) in enumerate(zip(plain, result)):
            if before != after:
                candidate[origins[index]] = after
        candidate = bytes(candidate)
        if formats.refpack_decode(candidate) == result:
            output = candidate
    if output is None:
        output = formats.refpack_encode(result) if compressed else result
    decoded = formats.refpack_decode(output) if compressed else output
    if decoded != result:
        raise ValueError('Memory configuration roundtrip failed')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError('Prepare a separate output before installation')
    result = prepare(args.input.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print('Prepared SaveLoadPP >= 24 MiB; other allocations preserved')


if __name__ == '__main__':
    main()
