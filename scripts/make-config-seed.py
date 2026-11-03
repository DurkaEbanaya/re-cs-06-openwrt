#!/usr/bin/env python3
"""Create an fstools-compatible private config seed without a gzip filename.

fstools identifies gzip by all four initial bytes: 1f 8b 08 00. A normal
tarfile.open(path, 'w:gz') includes FNAME (08) and is silently not restored.
No configuration data or passwords are printed by this utility.
"""
import argparse
import gzip
import io
from pathlib import Path
import tarfile


def encode(tar_bytes):
    source = io.BytesIO(tar_bytes)
    with tarfile.open(fileobj=source, mode='r:') as archive:
        names = set()
        for member in archive:
            path = Path(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or member.name in names or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe or duplicate configuration archive member')
            names.add(member.name)
    result = gzip.compress(tar_bytes, mtime=0)
    if result[:4] != bytes.fromhex('1f8b0800'):
        raise ValueError('Unsupported gzip header for fstools')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_tar', type=Path)
    parser.add_argument('output_tgz', type=Path)
    args = parser.parse_args()
    data = encode(args.input_tar.read_bytes())
    # Never overwrite an existing private seed or make it world-readable.
    import os
    fd = os.open(args.output_tgz, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


if __name__ == '__main__':
    main()
