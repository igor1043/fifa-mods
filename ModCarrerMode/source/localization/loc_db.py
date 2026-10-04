"""Strict FIFA 16 LanguageStrings reader/writer (PC T3DB, UTF-8 + Huffman).

Never reinterpret a DB as an ANSI/text file. The editor's Huffman encoder has
16-bit codes, so a valid-to-read tree with deeper codes is NOT safe to save.
Use the tree from the corresponding known-good original language instead.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _crc_table():
    result = []
    for value in range(256):
        crc = value << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)) & 0xffffffff
        result.append(crc)
    return result


_CRC = _crc_table()


def fifa_crc(data):
    crc = 0xffffffff
    for value in data:
        crc = ((crc << 8) ^ _CRC[((crc >> 24) ^ value) & 255]) & 0xffffffff
    return crc


class Tree:
    @classmethod
    def balanced(cls, symbols):
        """Deterministic length-limited fallback, never a frequency/22-bit tree."""
        symbols = sorted(set(symbols))
        if not 2 <= len(symbols) <= 256:
            raise ValueError("Unsupported Huffman alphabet")
        nodes = [[0, 0, 0, 0]]
        pending = [(0, symbols)]
        for index, group in pending:
            middle = len(group) // 2
            for side, half in enumerate((group[:middle], group[middle:])):
                if len(half) == 1:
                    nodes[index][side * 2 + 1] = half[0]
                else:
                    child = len(nodes)
                    nodes[index][side * 2] = child
                    nodes.append([0, 0, 0, 0])
                    pending.append((child, half))
        return cls(bytes(v for node in nodes for v in node))

    def __init__(self, raw):
        if not raw or len(raw) % 4 or len(raw) > 255 * 4:
            raise ValueError("Invalid Huffman tree size")
        self.raw = bytes(raw)
        self.nodes = list(struct.iter_unpack("BBBB", raw))
        self.codes = {}
        visited = set()

        def visit(node, code, depth):
            if node >= len(self.nodes) or node in visited or depth >= 32:
                raise ValueError("Invalid/cyclic Huffman tree")
            visited.add(node)
            n = self.nodes[node]
            for side in range(2):
                child, symbol = n[side * 2:side * 2 + 2]
                next_code = (code << 1) | side
                if child:
                    if symbol:
                        raise ValueError("Internal Huffman node has a leaf byte")
                    visit(child, next_code, depth + 1)
                else:
                    if symbol in self.codes:
                        raise ValueError("Duplicate Huffman symbol")
                    self.codes[symbol] = (next_code, depth + 1)
        visit(0, 0, 0)
        if len(visited) != len(self.nodes):
            raise ValueError("Unreachable Huffman nodes")
        self.max_bits = max(bits for _, bits in self.codes.values())
        self.lookup = []
        for value in range(4096):
            node = 0
            for depth in range(1, 13):
                side = (value >> (12 - depth)) & 1
                n = self.nodes[node]
                child, symbol = n[side * 2:side * 2 + 2]
                if not child:
                    self.lookup.append((symbol, depth, -1))
                    break
                node = child
            else:
                self.lookup.append((0, 12, node))

    def require_editor_safe(self):
        if self.max_bits > 16:
            raise ValueError(f"Huffman codes need {self.max_bits} bits; editor limit is 16")

    def decode(self, data, pointer, long_string, limit):
        if pointer == 0xffffffff:
            return ""
        prefix = 2 if long_string else 1
        if pointer < len(self.raw) or pointer + prefix > limit:
            raise ValueError("String pointer outside compressed block")
        count = int.from_bytes(data[pointer:pointer + prefix], "big")
        bitpos = (pointer + prefix) * 8
        output = bytearray()
        lookup, nodes = self.lookup, self.nodes
        for _ in range(count):
            p, offset = divmod(bitpos, 8)
            if p >= limit:
                raise ValueError("Truncated Huffman string")
            value = ((data[p] << 16) | (data[p + 1] << 8) | data[p + 2])
            symbol, bits, node = lookup[(value >> (12 - offset)) & 4095]
            bitpos += bits
            while node >= 0:
                if bitpos >= limit * 8:
                    raise ValueError("Truncated Huffman code")
                side = (data[bitpos // 8] >> (7 - bitpos % 8)) & 1
                n = nodes[node]
                child, symbol = n[side * 2:side * 2 + 2]
                bitpos += 1
                node = child if child else -1
            if bitpos > limit * 8:
                raise ValueError("Huffman string crosses block end")
            output.append(symbol)
        # Strict UTF-8: no replacement, Latin-1 fallback or double conversion.
        return output.decode("utf-8", errors="strict")

    def encode(self, text, long_string, *, allow_inherited_replacement=False):
        self.require_editor_safe()
        raw = text.encode("utf-8", errors="strict")
        if "\0" in text or ("\ufffd" in text and not allow_inherited_replacement):
            raise ValueError("NUL/replacement character in language text")
        width = 2 if long_string else 1
        if len(raw) >= 1 << (width * 8):
            raise ValueError("String exceeds compressed field byte-length prefix")
        out = bytearray(len(raw).to_bytes(width, "big"))
        reservoir = bits = 0
        for byte in raw:
            if byte not in self.codes:
                raise ValueError(f"Original tree cannot encode UTF-8 byte 0x{byte:02x}")
            code, length = self.codes[byte]
            reservoir = (reservoir << length) | code
            bits += length
            while bits >= 8:
                bits -= 8
                out.append((reservoir >> bits) & 255)
            reservoir &= (1 << bits) - 1
        if bits:
            out.append((reservoir << (8 - bits)) & 255)
        return bytes(out)


@dataclass
class LocDb:
    data: bytes
    rows: list
    tree: Tree
    table: int
    records: int
    block: int
    block_length: int

    @classmethod
    def read(cls, data, *, verify_crc=True, decode_rows=True):
        if len(data) < 124 or data[:8] != b"DB\x00\x08\0\0\0\0":
            raise ValueError("Not a PC FIFA 16 T3DB")
        if u32(data, 8) != len(data) or u32(data, 16) != 1 or data[24:28] != b"GJCv":
            raise ValueError("Unsupported LOC database/directory")
        table = 36 + u32(data, 28)
        if table != 36 or u32(data, table + 4) != 16 or data[table + 24] != 3:
            raise ValueError("Unsupported LanguageStrings record schema")
        descriptor = data[table + 36:table + 84]
        expected = (struct.pack("<II4sI", 14, 0, b"bYbZ", 32000) +
                    struct.pack("<II4sI", 3, 32, b"jKhj", 32) +
                    struct.pack("<II4sI", 13, 64, b"VhAs", 800))
        if descriptor != expected:
            raise ValueError("LanguageStrings field descriptors do not match")
        allocated, count = struct.unpack_from("<HH", data, table + 16)
        if not 0 < count <= allocated:
            raise ValueError("Invalid record counts")
        records = table + 84
        block = records + allocated * 16
        length = u32(data, table + 12)
        crcpos = block + ((length + 7) & ~7)
        if length < 4 or crcpos + 4 != len(data):
            raise ValueError("Compressed block/CRC exceeds DB")
        if verify_crc:
            for start, end in ((0, 20), (24, 32), (table, table + 32),
                               (table + 36, crcpos)):
                if fifa_crc(data[start:end]) != u32(data, end):
                    raise ValueError(f"LOC CRC mismatch at 0x{end:x}")
        pointers = [(u32(data, records + i * 16), u32(data, records + i * 16 + 8))
                    for i in range(count)]
        tree_size = min(p for pair in pointers for p in pair)
        if tree_size >= length:
            raise ValueError("No compressed strings")
        tree = Tree(data[block:block + tree_size])
        if not decode_rows:
            return cls(bytes(data), [], tree, table, records, block, length)
        compressed = data[block:block + length] + b"\0\0\0"
        rows = []
        cache = {}
        for i, (source, key) in enumerate(pointers):
            values = []
            for p, long_string in ((key, False), (source, True)):
                cache_key = (p, long_string)
                if cache_key not in cache:
                    cache[cache_key] = tree.decode(compressed, p, long_string, length)
                values.append(cache[cache_key])
            rows.append((u32(data, records + i * 16 + 4) - 2147483648, *values))
        return cls(bytes(data), rows, tree, table, records, block, length)

    def serialize(self, tree, rows=None):
        """Preserve schema, row IDs/order, allocation and record padding.

        Only compressed strings, their pointers, block size and CRCs change.
        Never build an unrestricted frequency tree as fifa-t3db used to do.
        """
        tree.require_editor_safe()
        rows = self.rows if rows is None else rows
        if len(rows) != len(self.rows):
            raise ValueError("This safe writer does not insert/delete rows")
        out = bytearray(self.data[:self.block])
        block = bytearray(tree.raw)
        cache = {}
        for i, (hashid, key, text) in enumerate(rows):
            if (hashid, key) != self.rows[i][:2]:
                raise ValueError("Cannot change language ID/hash/order")
            for value, long_string, field in ((text, True, 0), (key, False, 8)):
                inherited = value == self.rows[i][2 if long_string else 1]
                if "\0" in value or ("\ufffd" in value and not inherited):
                    raise ValueError("Invalid newly introduced language characters")
                old_pointer = u32(self.data, self.records + i * 16 + field)
                if not value and old_pointer == 0xffffffff:
                    continue
                cache_key = (value, long_string)
                if cache_key not in cache:
                    cache[cache_key] = len(block)
                    block.extend(tree.encode(value, long_string,
                                             allow_inherited_replacement=inherited))
                struct.pack_into("<I", out, self.records + i * 16 + field,
                                 cache[cache_key])
        block.extend(b"\0" * (-len(block) % 8))
        # Native/editor-produced originals include alignment in this length.
        # Using an unaligned value makes FifaLibrary's CRC pass seek early.
        length = len(block)
        out.extend(block)
        out.extend(b"\0" * 4)
        struct.pack_into("<I", out, 8, len(out))
        struct.pack_into("<I", out, self.table + 12, length)
        for start, end in ((0, 20), (24, 32), (self.table, self.table + 32),
                           (self.table + 36, len(out) - 4)):
            struct.pack_into("<I", out, end, fifa_crc(out[start:end]))
        return bytes(out)
