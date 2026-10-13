#!/usr/bin/env python3
"""Extract inline or external image data from a FIT, leaving the input intact."""
import argparse
import hashlib
import struct
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("image", type=Path)
p.add_argument("output", type=Path)
a = p.parse_args()
blob = a.image.read_bytes()
magic, total, nodes, strings, _, version, _, _, strings_size, nodes_size = struct.unpack_from(">10I", blob)
assert magic == 0xd00dfeed and version >= 17
assert max(total, nodes + nodes_size, strings + strings_size) <= len(blob)
cursor, stack, properties = nodes, [], {}
a.output.mkdir(parents=True, exist_ok=True)
while cursor < nodes + nodes_size:
    token = struct.unpack_from(">I", blob, cursor)[0]
    cursor += 4
    if token == 1:
        end = blob.index(b"\0", cursor, nodes + nodes_size)
        stack.append(blob[cursor:end].decode())
        cursor = (end + 4) & ~3
    elif token == 2:
        stack.pop()
    elif token == 3:
        size, name_offset = struct.unpack_from(">2I", blob, cursor)
        cursor += 8
        assert cursor + size <= nodes + nodes_size
        name_start = strings + name_offset
        assert strings <= name_start < strings + strings_size
        name = blob[name_start:blob.index(b"\0", name_start, strings + strings_size)].decode()
        path = "/".join(stack)
        if path.startswith("/images/") and path.count("/") == 2:
            properties.setdefault(path, {})[name] = (cursor, blob[cursor:cursor + size])
        cursor = (cursor + size + 3) & ~3
    elif token == 9:
        break
    elif token != 4:
        raise ValueError(f"unknown FDT token {token}")

for path, props in properties.items():
    if "data" in props:
        offset, data = props["data"]
    else:
        size = int.from_bytes(props["data-size"][1], "big")
        if "data-position" in props:
            offset = int.from_bytes(props["data-position"][1], "big")
        elif "data-offset" in props:
            offset = total + int.from_bytes(props["data-offset"][1], "big")
        else:
            continue
        assert offset + size <= len(blob)
        data = blob[offset:offset + size]
    target = a.output / (path.rsplit("/", 1)[1].replace("@", "-") + ".bin")
    target.write_bytes(data)
    print(path, "data_offset", hex(offset), "bytes", len(data),
          "sha256", hashlib.sha256(data).hexdigest())
