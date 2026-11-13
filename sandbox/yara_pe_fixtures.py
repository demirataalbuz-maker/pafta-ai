"""Inert PE32 byte fixtures for Pafta's YARA lessons.

Headers, import/export metadata and section bytes are synthetic. The code is
never executed, and the fixtures are only passed to libyara in memory.
"""
from __future__ import annotations

import struct


def pe_fixture(*, dll: str | None = "KERNEL32.dll", imported: str | None = "CreateFileW",
               exported: str | None = "LabEntry", export_base: int = 1,
               text_name: str = ".text", text_flags: int = 0x60000020,
               text_virtual_size: int = 0x100, data_flags: int = 0xC0000040) -> bytes:
    """Return a small PE-shaped DLL with controlled metadata, not runnable code."""
    image = bytearray(0x800)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", image, 0x84, 0x14C, 3, 0, 0, 0, 0xE0, 0x2102)
    optional = 0x98
    struct.pack_into("<H", image, optional, 0x10B)
    struct.pack_into("<I", image, optional + 16, 0x1000)
    struct.pack_into("<I", image, optional + 20, 0x1000)
    struct.pack_into("<I", image, optional + 28, 0x400000)
    struct.pack_into("<II", image, optional + 32, 0x1000, 0x200)
    struct.pack_into("<HH", image, optional + 40, 4, 0)
    struct.pack_into("<II", image, optional + 56, 0x4000, 0x200)
    struct.pack_into("<H", image, optional + 68, 3)
    struct.pack_into("<I", image, optional + 92, 16)
    # IMAGE_DATA_DIRECTORY: export (0), import (1).
    if exported is not None:
        struct.pack_into("<II", image, optional + 96, 0x3000, 0xB0)
    if dll is not None and imported is not None:
        struct.pack_into("<II", image, optional + 104, 0x2000, 0xD0)
    sections = ((text_name, text_virtual_size, 0x1000, 0x200, text_flags),
                (".idata", 0x100, 0x2000, 0x400, data_flags),
                (".edata", 0x100, 0x3000, 0x600, 0x40000040))
    for index, (name, size, rva, offset, flags) in enumerate(sections):
        encoded = name.encode("ascii")
        if len(encoded) > 8:
            raise ValueError("PE section names are at most eight ASCII bytes")
        header = 0x178 + 40 * index
        image[header:header + 8] = encoded.ljust(8, b"\0")
        struct.pack_into("<IIII", image, header + 8, size, rva, 0x200, offset)
        struct.pack_into("<I", image, header + 36, flags)
    image[0x200:0x207] = b"LABDATA"
    if dll is not None and imported is not None:
        dll_bytes, function_bytes = dll.encode("ascii"), imported.encode("ascii")
        if len(dll_bytes) > 24 or len(function_bytes) > 24:
            raise ValueError("fixture import name too long")
        struct.pack_into("<IIIII", image, 0x400, 0x2040, 0, 0, 0x2080, 0x2060)
        struct.pack_into("<II", image, 0x440, 0x20A0, 0)
        struct.pack_into("<II", image, 0x460, 0x20A0, 0)
        image[0x480:0x480 + len(dll_bytes) + 1] = dll_bytes + b"\0"
        image[0x4A2:0x4A2 + len(function_bytes) + 1] = function_bytes + b"\0"
    if exported is not None:
        name = exported.encode("ascii")
        if len(name) > 24:
            raise ValueError("fixture export name too long")
        struct.pack_into("<IIHHIIIIIII", image, 0x600, 0, 0, 0, 0, 0x3080,
                         export_base, 1, 1, 0x3040, 0x3050, 0x3060)
        struct.pack_into("<I", image, 0x640, 0x1000)
        struct.pack_into("<I", image, 0x650, 0x30A0)
        struct.pack_into("<H", image, 0x660, 0)
        image[0x680:0x68D] = b"PAFTALAB.dll\0"
        image[0x6A0:0x6A0 + len(name) + 1] = name + b"\0"
    return bytes(image)
