#!/usr/bin/env python3
"""Fetch pinned AWG recipes. Never install packages on a device or read secrets."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('cache', type=Path)
    args = parser.parse_args()
    lock = json.loads((REPO / 'extra-packages.lock.json').read_text())['amneziawg']
    if not args.cache.exists():
        subprocess.run(['git', 'clone', '--no-checkout', lock['url'], str(args.cache)], check=True)
        subprocess.run(['git', 'checkout', '--detach', lock['commit']], cwd=args.cache, check=True)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.cache, text=True).strip()
    if actual != lock['commit'] or subprocess.check_output(['git', 'status', '--porcelain'], cwd=args.cache):
        raise SystemExit('AWG recipe checkout must be pinned and clean')
    for package in lock['packages']:
        destination = args.source / 'package' / 're-cs-06-extra' / package
        if destination.exists():
            raise SystemExit(f'Refusing existing package directory {destination}')
        shutil.copytree(args.cache / package, destination)
    path = args.source / 'package/re-cs-06-extra/kmod-amneziawg/Makefile'
    text = path.read_text().replace('PKG_SOURCE_VERSION:=v$(PKG_VERSION)',
                                   'PKG_SOURCE_VERSION:=' + lock['kernel_source_commit'])
    # Modern kernel builds find their own headers via -C LINUX_DIR. Copying the
    # complete compiled kernel into every module build is neither needed nor safe
    # for bounded build storage. No AWG source changes are hidden here.
    block = ('define Build/Prepare\n\t$(call Build/Prepare/Default)\n'
             '\tmkdir -p $(PKG_BUILD_DIR)/$(MAKE_PATH)/kernel\n'
             '\t$(CP) $(LINUX_DIR)/* $(PKG_BUILD_DIR)/$(MAKE_PATH)/kernel/\nendef\n')
    if text.count(block) != 1:
        raise SystemExit('Pinned AWG recipe shape changed')
    text = text.replace(block, '')
    text = text.replace('PKG_RELEASE:=1', 'PKG_RELEASE:=1\nPKG_LICENSE:=GPL-2.0\nPKG_LICENSE_FILES:=COPYING')
    path.write_text(text)
    tools = args.source / 'package/re-cs-06-extra/amneziawg-tools/Makefile'
    tools.write_text(tools.read_text().replace('PKG_SOURCE_VERSION:=v$(PKG_VERSION)',
                                             'PKG_SOURCE_VERSION:=' + lock['tools_source_commit']))
    print('Pinned AWG recipes installed in build tree; no device contacted')


if __name__ == '__main__':
    main()
