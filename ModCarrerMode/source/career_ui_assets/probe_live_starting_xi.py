"""Read only the selected FIFA process; identify the exact loaded career APT."""
import ctypes
from ctypes import wintypes as w
import json
from pathlib import Path
import struct
import sys

K = ctypes.WinDLL("kernel32", use_last_error=True)
K.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
K.OpenProcess.restype = w.HANDLE
K.ReadProcessMemory.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
K.CloseHandle.argtypes = [w.HANDLE]


class Region(ctypes.Structure):
    _fields_ = [("base", ctypes.c_void_p), ("allocation", ctypes.c_void_p),
                ("allocation_protect", w.DWORD), ("partition", w.WORD),
                ("size", ctypes.c_size_t), ("state", w.DWORD),
                ("protect", w.DWORD), ("type", w.DWORD)]


K.VirtualQueryEx.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.POINTER(Region), ctypes.c_size_t]
K.VirtualQueryEx.restype = ctypes.c_size_t


def main():
    pid = int(sys.argv[1])
    handle = K.OpenProcess(0x410, False, pid)
    assert handle, ctypes.get_last_error()

    def read(address, size):
        data = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        K.ReadProcessMemory(handle, address, data, size, ctypes.byref(got))
        return data.raw[:got.value]

    marker = bytes.fromhex("b905a291b903af924f")
    address, matches, candidates, scanned = 0, [], [], 0
    while address < 0x7fffffffffff:
        region = Region()
        if not K.VirtualQueryEx(handle, address, ctypes.byref(region), ctypes.sizeof(region)):
            break
        base = region.base or 0
        end = base + region.size
        if end <= address:
            break
        if region.state == 0x1000 and not region.protect & (0x100 | 1):
            for chunk in range(base, end, 1024 * 1024):
                data = read(chunk, min(1024 * 1024 + len(marker), end - chunk))
                scanned += len(data)
                pos = 0
                while (pos := data.find(marker, pos)) >= 0:
                    match = chunk + pos
                    pos += 1
                    apt = match - 0x1fe8
                    candidates.append({"assignment": hex(match), "apt_prefix": read(apt, 16).hex(),
                                       "header": read(apt + 0x1ed8, 48).hex(), "memory_type": region.type})
                    if read(apt, 16) != b"Apt Data:1:7:8\x1a\0":
                        continue
                    header = read(apt + 0x1ed8, 48)
                    if len(header) != 48 or struct.unpack_from("<Q", header, 24)[0] != 447:
                        continue
                    matches.append({"apt": hex(apt), "assignment": hex(match),
                                    "body": hex(apt + 0x1f08), "body_size": 447,
                                    "allocation": hex(region.allocation), "protection": region.protect,
                                    "header": header.hex(), "patch_before": read(match, 13).hex()})
        address = end
    K.CloseHandle(handle)
    result = {"pid": pid, "scanned": scanned, "matches": matches, "candidates": candidates}
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
