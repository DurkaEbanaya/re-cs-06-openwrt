#!/usr/bin/env python3
"""Offline FIT integrity/structure checks. Never asserts hardware compatibility."""
import argparse
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import struct
import zlib


def fdt(data):
    magic, total, off_struct, off_strings, _, version, _, _, strings_size, struct_size = struct.unpack_from(">10I", data)
    assert magic == 0xD00DFEED and 17 <= version
    assert 40 <= total <= len(data)
    assert off_struct + struct_size <= total and off_strings + strings_size <= total
    strings = data[off_strings:off_strings + strings_size]
    nodes = {}
    stack = []
    offset = off_struct
    end = off_struct + struct_size
    terminated = False
    while offset < end:
        token, = struct.unpack_from(">I", data, offset)
        offset += 4
        if token == 1:
            stop = data.index(b"\0", offset, end)
            stack.append(data[offset:stop].decode())
            offset = (stop + 4) & ~3
            path = "/" + "/".join(stack[1:])
            assert path not in nodes
            nodes[path] = {}
        elif token == 2:
            assert stack
            stack.pop()
        elif token == 3:
            length, nameoff = struct.unpack_from(">2I", data, offset)
            offset += 8
            assert nameoff < len(strings) and offset + length <= end and stack
            name = strings[nameoff:strings.index(b"\0", nameoff)].decode()
            path = "/" + "/".join(stack[1:])
            assert name not in nodes[path]
            nodes[path][name] = data[offset:offset + length]
            offset = (offset + length + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            assert not stack
            terminated = True
            break
        else:
            raise ValueError(f"Invalid FDT token: {token}")
    assert terminated
    return total, nodes


def string(value):
    return value.rstrip(b"\0").decode()


def inspect(data, persistent=True):
    total, nodes = fdt(data)
    config = string(nodes["/configurations"]["default"])
    assert config == "config@mi01.6", config
    selected = nodes["/configurations/" + config]
    result = {"fit_bytes": total, "file_bytes": len(data), "default_config": config,
              "images": [], "hardware_boot_tested": False}
    for role in ("kernel", "fdt"):
        name = string(selected[role])
        path = "/images/" + name
        props = nodes[path]
        image = props["data"]
        hashes = []
        for child, fields in nodes.items():
            if not child.startswith(path + "/hash") or child.count("/") != 3:
                continue
            algo = string(fields["algo"])
            actual = struct.pack(">I", zlib.crc32(image)) if algo == "crc32" else hashlib.new(algo, image).digest()
            assert actual == fields["value"], f"FIT hash mismatch: {name}/{algo}"
            hashes.append(algo)
        assert hashes, f"Missing hashes: {name}"
        record = {"role": role, "bytes": len(image), "hash_algorithms_verified": hashes,
                  "sha256": hashlib.sha256(image).hexdigest()}
        if role == "kernel":
            assert string(props["arch"]) == "arm64" and string(props["os"]) == "linux"
            compression = string(props["compression"])
            assert compression in ("gzip", "lzma")
            raw = gzip.decompress(image) if compression == "gzip" else lzma.decompress(image)
            assert raw[56:60] == b"ARM\x64", "Not an ARM64 Linux Image"
            record.update(compression=compression, uncompressed_bytes=len(raw),
                          load=int.from_bytes(props["load"], "big"), entry=int.from_bytes(props["entry"], "big"))
        else:
            _, tree = fdt(image)
            assert b"jdcloud,re-cs-06\0" in tree["/"]["compatible"]
            assert not any("nvmem-cells" in props for props in tree.values()), "Unexpected MAC NVMEM dependency"
            record["device_tree_model"] = string(tree["/"]["model"])
            record["no_nvmem_mac_dependency"] = True
        result["images"].append(record)
    if persistent:
        assert len(data) <= 7 * 1024 * 1024, "Kernel exceeds 7 MiB HLOS slot"
    result["persistent_slot_limit_checked"] = persistent
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--initramfs", action="store_true")
    args = parser.parse_args()
    print(json.dumps(inspect(args.image.read_bytes(), not args.initramfs), indent=2))
