#!/usr/bin/env python3
"""Archive corresponding build sources; exclude keys, work state and unused binary firmware."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


def patched_paths(repo):
    """Include new source files created by public patches, not arbitrary untracked work."""
    names = set()
    for patch in (repo / 'patches').glob('*.patch'):
        for name in re.findall(r'^\+\+\+ b/(.+)$', patch.read_text(), re.M):
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts
            assert path.parts[0] not in ('.git', 'files', 'tmp', 'build_dir', 'staging_dir')
            names.add(name)
    return names


def package(source, output):
    repo = Path(__file__).resolve().parents[1]
    assert not output.exists()
    omitted = []
    inputs = []
    trees = [(source, "lede"), (repo, "recipe")]
    trees += [(source / "feeds" / name, "lede/feeds/" + name) for name in ("packages", "luci", "routing")]
    for tree, prefix in trees:
        names = {raw.decode() for raw in subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=tree).split(b"\0") if raw}
        if tree == source:
            names |= patched_paths(repo)
        for name in sorted(names):
            path = tree / name
            assert path.is_file() or path.is_symlink(), name
            if not path.is_symlink():
                data = path.read_bytes()
                if b"\0" in data[:8192] and path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf"):
                    omitted.append({"tree": prefix, "path": name, "sha256": hashlib.sha256(data).hexdigest(),
                                    "reason": "non-source binary not part of external-radio build"})
                    continue
            inputs.append((path, prefix + "/" + name))
    for path in sorted((source / "dl").iterdir()):
        if not path.is_file() or path.name.startswith(("ath-fw-", "broadcom-wl-", "ipq-wifi-")):
            continue
        inputs.append((path, "lede/dl/" + path.name))
    # Only selected, reviewed configuration/overlay; never keys or build_dir.
    for name in (".config", "feeds.conf"):
        inputs.append((source / name, "lede/" + name))
    for path in (source / "files").rglob("*"):
        if path.is_file():
            assert path.suffix not in (".key", ".pem")
            assert 'lib/firmware/' not in path.relative_to(source / 'files').as_posix(), \
                "External-radio source bundle must not include a local firmware overlay"
            inputs.append((path, "lede/" + path.relative_to(source).as_posix()))
    process = subprocess.Popen(["zstd", "-T2", "-3", "-o", str(output)], stdin=subprocess.PIPE)
    manifest = []
    with tarfile.open(fileobj=process.stdin, mode="w|") as archive:
        for path, name in inputs:
            archive.add(path, arcname=name, recursive=False)
            if not path.is_symlink():
                manifest.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        import io
        for name, value in (("SOURCE-FILES.json", manifest), ("OMITTED-UNUSED-BINARIES.json", omitted)):
            data = (json.dumps(value, indent=2) + "\n").encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    process.stdin.close()
    assert process.wait() == 0
    subprocess.run(["zstd", "-t", str(output)], check=True)
    return {"source_files": len(manifest), "omitted_unused_binaries": len(omitted),
            "bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.source.resolve(), args.output.resolve()), indent=2))
