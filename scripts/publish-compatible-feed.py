#!/usr/bin/env python3
"""Explicitly publish a frozen, signed package feed as GitHub release assets.

Never changes router settings, updates an existing release or uploads a signing
key. Use only a reviewed source commit already pushed to the public repository.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('feed', type=Path)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--source-archive', required=True, type=Path,
                        help='Audited corresponding package sources (no private radio overlay)')
    parser.add_argument('--confirm-public-packages', action='store_true')
    args = parser.parse_args()
    if not args.confirm_public_packages or not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        raise ValueError('Explicit public-package confirmation and full source commit required')
    root = args.feed.resolve()
    repository = json.loads(subprocess.check_output(['gh', 'api', f'repos/{args.repo}']))
    if repository['private'] or repository['full_name'] != args.repo:
        raise ValueError('An explicitly named PUBLIC repository is required for anonymous opkg access')
    commit = json.loads(subprocess.check_output(['gh', 'api', f'repos/{args.repo}/commits/{args.commit}']))
    if commit['sha'] != args.commit:
        raise ValueError('Reviewed commit is not available in the destination repository')
    manifest = json.loads((root/'feed-manifest.json').read_text())
    if not re.fullmatch(re.escape('packages-r19-'+manifest['kernel_abi'])+r'(?:-feed[2-9][0-9]*)?', args.tag):
        raise ValueError('Tag must bind to this exact r19 ABI')
    sources = args.source_archive.resolve()
    if not sources.is_file() or not re.fullmatch(r'corresponding-package-sources-r19\.tar\.zst', sources.name):
        raise ValueError('Audited corresponding package-source archive required')
    expected = {row['filename'] for row in manifest['packages']}
    expected |= {'Packages', 'Packages.gz', 'Packages.sig', 'feed-key.pub', 'feed-manifest.json', 'SHA256SUMS'}
    if {p.name for p in root.iterdir()} != expected or 'kernel' in {r['package'] for r in manifest['packages']}:
        raise ValueError('Unexpected feed files or fake kernel package')
    if gzip.decompress((root/'Packages.gz').read_bytes()) != (root/'Packages').read_bytes():
        raise ValueError('Compressed index differs')
    subprocess.run(['usign', '-V', '-m', str(root/'Packages'), '-p', str(root/'feed-key.pub'),
                    '-x', str(root/'Packages.sig')], check=True)
    for row in manifest['packages']:
        if hashlib.sha256((root/row['filename']).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Package hash changed: '+row['filename'])
    spec = importlib.util.spec_from_file_location('feed', Path(__file__).with_name('package-compatible-feed.py'))
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    for row in manifest['packages']:
        feed.check_public_payload(root/row['filename'])
    for line in (root/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        if Path(name).name != name or hashlib.sha256((root/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Feed checksum mismatch')
    existing = json.loads(subprocess.check_output(['gh', 'api', f'repos/{args.repo}/releases?per_page=100']))
    if any(r['tag_name'] == args.tag for r in existing):
        raise ValueError('Release already exists; inspect it, never overwrite a frozen feed')
    notes = ('Matching r19 packages, kernel ABI `'+manifest['kernel_abi']+'`.\n\n'
             'Do not use on r18 or official OpenWrt; never install all packages or force dependencies. '
             'SQM and alternative modem managers require deliberate owner configuration. '
             'Package index is signed; firmware/signing private keys are not included.\n')
    with tempfile.TemporaryDirectory() as td:
        path = Path(td)/'notes.md'; path.write_text(notes)
        source_sum = Path(td)/'SOURCE-SHA256SUMS'
        digest = hashlib.sha256()
        with sources.open('rb') as source:
            while chunk := source.read(1024*1024):
                digest.update(chunk)
        source_sum.write_text(digest.hexdigest()+'  '+sources.name+'\n')
        subprocess.run(['gh', 'release', 'create', args.tag, '--repo', args.repo,
                        '--target', args.commit, '--title', 'r19 matching packages: '+manifest['kernel_abi'],
                        '--prerelease', '--notes-file', str(path)] +
                       [str(root/name) for name in sorted(expected)] + [str(sources), str(source_sum)], check=True)
        expected |= {sources.name, source_sum.name}
        source_sum_bytes = source_sum.read_bytes()
    release = json.loads(subprocess.check_output(['gh', 'api', f'repos/{args.repo}/releases/tags/{args.tag}']))
    # The embedded release response caps assets at 100; this feed is larger.
    assets = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp',
        f'repos/{args.repo}/releases/{release["id"]}/assets?per_page=100']))
    assets = [asset for page in assets for asset in page]
    if {r['name'] for r in assets} != expected:
        raise ValueError('Incomplete upload; inspect release, do not recreate blindly')
    for row in assets:
        if row['name'] == sources.name:
            wanted = digest.hexdigest()
        elif row['name'] == 'SOURCE-SHA256SUMS':
            wanted = hashlib.sha256(source_sum_bytes).hexdigest()
        else:
            wanted = hashlib.sha256((root/row['name']).read_bytes()).hexdigest()
        if row['state'] != 'uploaded' or row['digest'] != 'sha256:'+wanted:
            raise ValueError('Remote digest differs: '+row['name'])
    print(json.dumps(dict(url=release['html_url'], assets=len(expected), all_asset_sha256_verified=True)))


if __name__ == '__main__':
    main()
