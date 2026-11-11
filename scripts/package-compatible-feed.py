#!/usr/bin/env python3
"""Create a signed, dependency-closed offline feed for ONE exact built image.

Never contacts a router, publishes packages, exports a private signing key or
forces an opkg dependency. Refuses ambiguous/stale package versions.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOTS = [
    'wireguard-tools', 'luci-proto-wireguard', 'kmod-veth', 'kmod-tun',
    'amneziawg-tools', 'luci-proto-amneziawg', 'kmod-nft-queue',
    'kmod-nft-nat', 'kmod-nft-offload', 'libnetfilter-queue', 'libmnl',
    'libcap', 'zlib', 'nftables-json', 'curl', 'gzip', 'coreutils-sort', 'coreutils-sleep',
    'sms-tool', 'comgt', 'kmod-usb-serial-qualcomm', 'kmod-usb-net-rndis',
    'kmod-usb-net-cdc-ether', 'kmod-usb-net-cdc-mbim', 'kmod-usb-net-qmi-wwan',
    'kmod-usb-net-huawei-cdc-ncm', 'kmod-usb-serial-option', 'kmod-usb-acm',
    'usb-modeswitch', 'coreutils-stty', 'qmi-utils', 'mbim-utils', 'modemmanager',
    'luci-proto-qmi', 'luci-proto-mbim', 'luci-proto-modemmanager', 'adb',
    'kmod-nf-socket', 'kmod-nft-socket',
    'kmod-ifb', 'kmod-sched-core', 'kmod-sched-cake', 'tc-full',
    'sqm-scripts', 'luci-app-sqm', 'kmod-ipvlan', 'kmod-dummy',
    'kmod-br-netfilter', 'kmod-gre', 'kmod-gre6', 'kmod-vxlan',
    'kmod-ipip', 'kmod-sit', 'kmod-fs-exfat', 'kmod-fs-vfat', 'kmod-fs-ntfs3',
    'kmod-nls-cp437', 'kmod-nls-iso8859-1', 'kmod-nls-utf8',
]


def fields(text):
    result = {}
    last = None
    for line in text.splitlines():
        if line.startswith((' ', '\t')) and last:
            result[last] += '\n' + line
        elif ': ' in line:
            last, value = line.split(': ', 1)
            if last in result:
                raise ValueError('Duplicate package field')
            result[last] = value
    return result


def control(path):
    with tarfile.open(path, 'r:gz') as outer:
        member = next(m for m in outer if m.name.lstrip('./') == 'control.tar.gz')
        data = outer.extractfile(member).read()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as inner:
        member = next(m for m in inner if m.name.lstrip('./') == 'control')
        return fields(inner.extractfile(member).read().decode())


def check_public_payload(path):
    """The downloadable feed must not carry blobs or unsafe archive paths."""
    with tarfile.open(path, 'r:gz') as archive:
        member = next(m for m in archive if m.name.lstrip('./') == 'data.tar.gz')
        data = archive.extractfile(member).read()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive:
            name = Path(member.name.removeprefix('./'))
            if (name.is_absolute() or '..' in name.parts or name.as_posix().startswith('lib/firmware/')
                    or not (member.isfile() or member.isdir() or member.issym())):
                raise ValueError('Unsafe path or firmware in public package: ' + path.name)


def collect_records(paths, selected, kernel_version):
    records = {}
    for path in sorted(paths):
        row = control(path)
        name = row['Package']
        if name != 'kernel' and row.get('SourceName', name) not in selected and name not in selected:
            continue
        if name.startswith('kmod-') and not re.search(r'kernel\s*\(=\s*' + re.escape(kernel_version) + r'\)', row.get('Depends', '')):
            continue
        if row['Architecture'] not in ('all', 'noarch', 'aarch64_cortex-a53'):
            raise SystemExit(f'Wrong architecture: {path.name}')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if name in records and records[name]['sha256'] != digest:
            raise SystemExit(f'Ambiguous package {name}; remove neither artifact blindly, inspect build provenance')
        records[name] = dict(control=row, path=path, sha256=digest)
    return records


def dependency_closure(records, roots, kernel_version, compare=None):
    providers = {}
    for name, row in records.items():
        for alias in [name, row['control'].get('SourceName', name)] + row['control'].get('Provides', '').split(', '):
            alias = alias.split(' ', 1)[0]
            if alias:
                providers.setdefault(alias, set()).add(name)
    closure = set()
    satisfied_kernel = False

    def require(expression):
        nonlocal satisfied_kernel
        alternatives = [p.strip() for p in expression.split('|')]
        for alternative in alternatives:
            match = re.fullmatch(r'([a-zA-Z0-9+_.-]+)(?:\s*\(([^)]+)\))?', alternative)
            if not match:
                raise ValueError('Unrecognized dependency: ' + alternative)
            name, version = match.groups()
            if name == 'kernel':
                if not version or not re.fullmatch(r'=\s*' + re.escape(kernel_version), version):
                    raise ValueError('Kernel ABI mismatch: ' + alternative)
                satisfied_kernel = True
                return
            candidates = {name} if name in records else providers.get(name, set())
            # SQM depends on virtual "tc". Prefer the reviewed full variant,
            # never ship/install tiny+bpf+full simultaneously just to resolve it.
            if name == 'tc' and 'tc-full' in candidates:
                candidates = {'tc-full'}
            if len(candidates) != 1:
                continue
            chosen = next(iter(candidates))
            # Versioned runtime libraries are resolved by their ABI package name.
            # For additional version constraints, use the build's host opkg
            # comparator instead of approximating OpenWrt version semantics.
            if version:
                comparison = re.fullmatch(r'(<<|<=|>=|>>|=|<|>)\s*(\S+)', version)
                if not comparison:
                    raise ValueError('Unrecognized version constraint: ' + alternative)
                op, wanted = comparison.groups()
                if compare is None:
                    raise ValueError('Host opkg comparator required: ' + alternative)
                if not compare(records[chosen]['control']['Version'], op, wanted):
                    continue
            if chosen in closure:
                return
            closure.add(chosen)
            for dependency in records[chosen]['control'].get('Depends', '').split(','):
                if dependency.strip():
                    require(dependency.strip())
            return
        raise ValueError('Missing or ambiguous compatible dependency: ' + expression)

    for name in roots:
        require(name)
    return closure, satisfied_kernel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists():
        raise SystemExit('Refusing existing output')
    config = (source / '.config').read_text()
    selected = set(re.findall(r'^CONFIG_PACKAGE_([^=]+)=[ym]$', config, re.M))
    kernels = list((source / 'bin/targets/qualcommbe/ipq53xx/packages').glob('kernel_*.ipk'))
    if len(kernels) != 1:
        raise ValueError('Exactly one current kernel package required')
    kernel_version = control(kernels[0])['Version']
    records = collect_records((source / 'bin').rglob('*.ipk'), selected, kernel_version)

    def compare(actual, op, wanted):
        comparator = source / 'staging_dir/host/bin/opkg'
        if not comparator.exists():
            raise ValueError('Host opkg comparator required')
        result = subprocess.run([str(comparator), 'compare-versions', actual, op, wanted], capture_output=True)
        if result.returncode not in (0, 1):
            raise ValueError('Host opkg comparator failed')
        return result.returncode == 0

    closure, satisfied_kernel = dependency_closure(records, ROOTS, kernel_version, compare)
    if not satisfied_kernel:
        raise ValueError('No verified kernel dependency')
    output.mkdir(mode=0o755)
    index = []
    manifest = []
    for name in sorted(closure):
        item = records[name]
        # This feed is publicly downloadable even when full radio images are
        # private. Never export radio blobs via a transitive dependency.
        check_public_payload(item['path'])
        filename = item['path'].name
        shutil.copyfile(item['path'], output / filename)
        row = dict(item['control'], Filename=filename, Size=str(item['path'].stat().st_size), SHA256sum=item['sha256'])
        index.append('\n'.join(f'{key}: {value}' for key, value in row.items()) + '\n\n')
        manifest.append(dict(package=name, version=row['Version'], filename=filename, sha256=item['sha256']))
    packages = ''.join(index).encode()
    (output / 'Packages').write_bytes(packages)
    (output / 'Packages.gz').write_bytes(gzip.compress(packages, mtime=0))
    usign = source / 'staging_dir/host/bin/usign'
    public = source / 'key-build.pub'
    subprocess.run([str(usign), '-S', '-m', str(output / 'Packages'), '-s', str(source / 'key-build'), '-x', str(output / 'Packages.sig')], check=True)
    subprocess.run([str(usign), '-V', '-m', str(output / 'Packages'), '-p', str(public), '-x', str(output / 'Packages.sig')], check=True)
    shutil.copyfile(public, output / 'feed-key.pub')
    report = dict(kernel_abi=kernel_version, arch='aarch64_cortex-a53',
                  config_sha256=hashlib.sha256(config.encode()).hexdigest(),
                  dependency_closure_checked=True, signature_verified=True,
                  kernel_package_intentionally_not_distributed=True, packages=manifest)
    (output / 'feed-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    sums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
                   for path in sorted(output.iterdir()) if path.is_file())
    (output / 'SHA256SUMS').write_text(sums)
    print(json.dumps(dict(packages=len(closure), kernel_abi=kernel_version, signed=True)))


if __name__ == '__main__':
    main()
