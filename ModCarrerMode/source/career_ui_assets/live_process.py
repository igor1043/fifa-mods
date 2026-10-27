"""Shared Win32 access definitions for the selected FIFA process only."""
import ctypes
from ctypes import wintypes as w
import json
from pathlib import Path
import struct
import sys
import pefile
from probe_live_starting_xi import K


class Module(ctypes.Structure):
    _fields_ = [("size", w.DWORD), ("id", w.DWORD), ("pid", w.DWORD),
                ("global_usage", w.DWORD), ("usage", w.DWORD), ("base", ctypes.c_void_p),
                ("bytes", w.DWORD), ("handle", w.HMODULE), ("name", w.WCHAR * 256),
                ("path", w.WCHAR * 260)]


K.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
K.CreateToolhelp32Snapshot.restype = w.HANDLE
K.Module32FirstW.argtypes = [w.HANDLE, ctypes.POINTER(Module)]
K.Module32NextW.argtypes = K.Module32FirstW.argtypes
K.VirtualAllocEx.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.c_size_t, w.DWORD, w.DWORD]
K.VirtualAllocEx.restype = ctypes.c_void_p
K.VirtualFreeEx.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.c_size_t, w.DWORD]
K.WriteProcessMemory.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
K.CreateRemoteThread.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
K.CreateRemoteThread.restype = w.HANDLE
K.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
K.GetExitCodeThread.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
K.GetModuleHandleW.argtypes = [w.LPCWSTR]
K.GetModuleHandleW.restype = w.HMODULE
K.GetProcAddress.argtypes = [w.HMODULE, ctypes.c_char_p]
K.GetProcAddress.restype = ctypes.c_void_p
K.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]


def modules(pid):
    snapshot = K.CreateToolhelp32Snapshot(0x18, pid)
    assert snapshot and snapshot != ctypes.c_void_p(-1).value
    value = Module(); value.size = ctypes.sizeof(value)
    result = {}
    valid = K.Module32FirstW(snapshot, ctypes.byref(value))
    while valid:
        result[value.name.lower()] = {"base": value.base, "size": value.bytes, "path": value.path}
        valid = K.Module32NextW(snapshot, ctypes.byref(value))
    K.CloseHandle(snapshot)
    return result
