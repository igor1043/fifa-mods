import io
import random
import struct
import unittest

from fifa_formats import (big_directory, build_big, identify, refpack_decode,
                          refpack_encode, unpack_big_bytes)


class FormatTests(unittest.TestCase):
    def test_reference_tokens_and_overlap(self):
        # Hand-built streams; tests do not obtain expected data from the encoder.
        vectors = [
            (b'\xfc', b''),
            (b'\xffabc', b'abc'),
            (b'\xe0abcd\xfc', b'abcd'),
            (b'\x01\x00a\xfc', b'aaaa'),
            (b'\x80\x40\x00a\xfc', b'aaaaa'),
            (b'\xc1\x00\x00\x00a\xfc', b'aaaaaa'),
            (b'\xe0abcd\x0c\x03\xfc', b'abcdabcdab'),
        ]
        for commands, decoded in vectors:
            encoded = b'\x10\xfb' + len(decoded).to_bytes(3, 'big') + commands
            self.assertEqual(refpack_decode(encoded), decoded)

    def test_roundtrip_boundaries_and_actual_compression(self):
        rng = random.Random(160930)
        for size in (0, 1, 2, 3, 4, 10, 67, 111, 112, 113, 1028, 4096, 18000):
            for raw in (rng.randbytes(size), (b'FIFA16 stadium XML\r\n' * size)[:size], b'A' * size):
                self.assertEqual(refpack_decode(refpack_encode(raw)), raw)
        raw = b'fixture,club,stadium\r\n' * 2000
        self.assertLess(len(refpack_encode(raw)), len(raw) // 4)

    def test_malformed_streams_rejected(self):
        for data in (b'', b'\x10\xfb\x00\x00\x04\xfc',
                     b'\x10\xfb\x00\x00\x03\x00\x00\xfc',
                     b'\x10\xfb\x00\x00\x04\xe0ab',
                     b'\x10\xfb\x00\x00\x00\xfcEXTRA'):
            with self.assertRaises(ValueError):
                refpack_decode(data)

    def test_directory_duplicate_names_and_order(self):
        entries = [('same.xml', b'one'), ('same.xml', b'two'), ('../inert', b''), ('0', b'Apt Data:1:7:8')]
        for magic in ('BIG4', 'BIGF'):
            data = build_big(entries, magic=magic, trailer=b'opaque00')
            info, reread = unpack_big_bytes(data)
            self.assertEqual(entries, reread)
            self.assertEqual(info['directory_trailer_hex'], b'opaque00'.hex())
            self.assertEqual(info['size_endian'], 'little')

    def test_reference_wide_distance_and_long_length(self):
        # Independent literal producer, then explicit max-distance copy tokens.
        for distance, token, length in ((1024, b'\x7c\xff', 10),
                                        (16384, b'\xbf\x3f\xff', 67),
                                        (131072, b'\xdc\xff\xff\xff', 1028)):
            prefix = random.Random(distance).randbytes(distance)
            literal = bytearray()
            for pos in range(0, len(prefix), 112):
                chunk = prefix[pos:pos+112]
                literal.append(0xe0 + len(chunk)//4 - 1)
                literal.extend(chunk)
            expected = prefix + prefix[:length]
            stream = b'\x10\xfb' + len(expected).to_bytes(3,'big') + literal + token + b'\xfc'
            self.assertEqual(refpack_decode(stream), expected)
            self.assertEqual(refpack_decode(refpack_encode(expected)), expected)

    def test_output_guards(self):
        import tempfile
        from pathlib import Path
        from fifa_formats import outside_input
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                outside_input(root/'input', root/'game'/'output', root/'game')
            with self.assertRaises(ValueError):
                outside_input(root/'input', root/'input', root/'game')
            outside_input(root/'input', root/'new', root/'game')

    def test_corrupt_directory_rejected(self):
        data = bytearray(build_big([('x', b'abc')]))
        struct.pack_into('>I', data, 16, len(data) + 1)
        with self.assertRaises(ValueError):
            big_directory(io.BytesIO(data), len(data))
        self.assertEqual(identify(b'\x10\xfb\x00\x01\x00'), 'RefPack-10FB')

    def test_chunkzip_observed_dialect(self):
        from fifa_formats import chunkzip_decode_single, chunkzip_encode_single
        for data in (b'', b'BIG4' * 500, random.Random(3).randbytes(0x2d000)):
            packed = chunkzip_encode_single(data)
            self.assertEqual(chunkzip_decode_single(packed), data)
            with self.assertRaises(ValueError):
                chunkzip_decode_single(packed + b'garbage')
            bad = bytearray(packed)
            struct.pack_into('>I', bad, 20, 2)
            with self.assertRaises(ValueError):
                chunkzip_decode_single(bad)


if __name__ == '__main__':
    unittest.main()
