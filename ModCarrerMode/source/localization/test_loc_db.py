import struct
import unittest

from loc_db import LocDb, Tree, fifa_crc


class LocaleTests(unittest.TestCase):
    def setUp(self):
        self.tree = Tree.balanced(range(256))

    def test_utf8_all_languages_and_lengths(self):
        for text in ("COMPETI\u00c7\u00c3O", "P\u00fablico", "CD \u00d1ublense", "\u015e\u011f\u0131",
                     "\u0421\u043e\u0441\u0442\u0430\u0432", "\u7403\u54e1", "\u0644\u0627\u0639\u0628", "line\nnext", "", "&;=|\\*"):
            for long_string in (False, True):
                encoded = self.tree.encode(text, long_string)
                width = 2 if long_string else 1
                self.assertEqual(int.from_bytes(encoded[:width], "big"), len(text.encode("utf-8")))
                data = self.tree.raw + encoded + b"\0\0\0"
                self.assertEqual(self.tree.decode(data, len(self.tree.raw), long_string,
                                                 len(data) - 3), text)
        self.assertEqual(self.tree.max_bits, 8)

    def test_length_counts_bytes_not_characters(self):
        self.tree.encode("\u00e7" * 127, False)
        with self.assertRaises(ValueError):
            self.tree.encode("\u00e7" * 128, False)

    def test_invalid_characters_refused(self):
        for text in ("bad\0", "bad\ufffd"):
            with self.assertRaises(ValueError):
                self.tree.encode(text, True)
        with self.assertRaises(UnicodeDecodeError):
            data = self.tree.raw + bytes([1, 0xff]) + b"\0\0\0"
            self.tree.decode(data, len(self.tree.raw), False, len(data) - 3)

    def test_deep_tree_refused_for_writing(self):
        nodes = [[i + 1, 0, 0, i] for i in range(18)]
        nodes[-1] = [0, 18, 0, 17]
        tree = Tree(bytes(v for node in nodes for v in node))
        self.assertEqual(tree.max_bits, 18)
        with self.assertRaises(ValueError):
            tree.encode("a", True)

    def test_crc_reference(self):
        self.assertEqual(fifa_crc(b"123456789"), 0x0376e6e7)

    def test_complete_db_roundtrip_and_guards(self):
        # A minimal real schema with null/empty values and record padding.
        header = bytearray(120 + 3 * 16)
        header[:8] = b"DB\x00\x08\0\0\0\0"
        struct.pack_into("<I", header, 16, 1)
        header[24:28] = b"GJCv"
        struct.pack_into("<I", header, 40, 16)
        struct.pack_into("<HH", header, 52, 3, 3)
        header[60] = 3
        header[72:120] = (struct.pack("<II4sI", 14, 0, b"bYbZ", 32000) +
                          struct.pack("<II4sI", 3, 32, b"jKhj", 32) +
                          struct.pack("<II4sI", 13, 64, b"VhAs", 800))
        values = [(1, "Test", "COMPETI\u00c7\u00c3O"), (2, "Empty", ""), (3, "Null", "")]
        block = bytearray(self.tree.raw)
        for i, (h, key, text) in enumerate(values):
            pointers = []
            for value, long_string in ((text, True), (key, False)):
                pointers.append(len(block))
                block.extend(self.tree.encode(value, long_string))
            if i == 2:
                pointers[0] = 0xffffffff
            struct.pack_into("<IIII", header, 120 + i * 16, pointers[0], h + 2147483648,
                             pointers[1], 0xaabbccdd)
        struct.pack_into("<I", header, 48, len(block))
        block.extend(b"\0" * (-len(block) % 8))
        data = header + block + b"\0" * 4
        struct.pack_into("<I", data, 8, len(data))
        for start, end in ((0, 20), (24, 32), (36, 68), (72, len(data) - 4)):
            struct.pack_into("<I", data, end, fifa_crc(data[start:end]))
        db = LocDb.read(data)
        self.assertEqual(db.rows, values)
        corrected = db.serialize(self.tree)
        reopened = LocDb.read(corrected)
        self.assertEqual(reopened.rows, values)
        self.assertEqual(reopened.serialize(self.tree), corrected)
        self.assertEqual(struct.unpack_from("<I", corrected, 152)[0], 0xffffffff)
        with self.assertRaises(ValueError):
            db.serialize(self.tree, values[:-1])
        changed = list(values)
        changed[0] = (1, "OtherKey", "text")
        with self.assertRaises(ValueError):
            db.serialize(self.tree, changed)
        damaged = bytearray(corrected)
        damaged[20] ^= 1
        with self.assertRaises(ValueError):
            LocDb.read(damaged)


if __name__ == "__main__":
    unittest.main()
