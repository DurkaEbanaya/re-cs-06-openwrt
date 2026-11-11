#!/usr/bin/env python3
"""Embed ONE immutable HTTPS feed URL for the current built kernel. No publishing."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


def marker(kernel, url, fingerprint):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or not re.fullmatch(r'https://[A-Za-z0-9._~/%+-]+', url)
            or kernel not in url or not re.fullmatch(r'[a-zA-Z0-9.+_-]+', kernel)
            or not re.fullmatch(r'[a-f0-9]{16}', fingerprint)):
        raise ValueError('Require an exact-kernel immutable HTTPS URL without credentials and a public key fingerprint')
    return f'1\n{kernel}\n{url.rstrip("/")}\n{fingerprint}\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('url', help='Release-specific URL containing the exact kernel package version')
    args = parser.parse_args()
    source = args.source.resolve()
    spec = importlib.util.spec_from_file_location('feed', Path(__file__).with_name('package-compatible-feed.py'))
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    kernels = list((source/'bin/targets/qualcommbe/ipq53xx/packages').glob('kernel_*.ipk'))
    if len(kernels) != 1:
        raise ValueError('Exactly one current built kernel package required')
    kernel = feed.control(kernels[0])['Version']
    fingerprint = subprocess.check_output([str(source/'staging_dir/host/bin/usign'), '-F',
                                           '-p', str(source/'key-build.pub')], text=True).strip()
    data = marker(kernel, args.url, fingerprint)
    path = source/'files/usr/share/re-cs-06/release-feed'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    path.chmod(0o644)
    print(f'Embedded feed binding for kernel {kernel}; rebuild image before distribution.')


if __name__ == '__main__':
    main()
