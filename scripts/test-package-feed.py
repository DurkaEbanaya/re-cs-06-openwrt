#!/usr/bin/env python3
"""Host-only opkg test with a disposable offline root; never installs packages.

SOURCE supplies the native host opkg/usign built by this tree. --url permits a
real HTTPS release test; without it an ephemeral localhost HTTP server is used.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import threading


def test_feed(source, feed, url=None):
    source, feed = source.resolve(), feed.resolve()
    tools = source/'staging_dir/host/bin'
    abi = json.loads((feed/'feed-manifest.json').read_text())['kernel_abi']
    server = None
    if url is None:
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_args):
                pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
                   functools.partial(QuietHandler, directory=str(feed)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = 'http://127.0.0.1:'+str(server.server_port)
    elif not url.startswith('https://'):
        raise ValueError('External feed must use HTTPS')
    log = bytearray()
    try:
        with tempfile.TemporaryDirectory(prefix='recs06-feed-') as td:
            work = Path(td)
            root = work/'root'
            (root/'usr/lib/opkg/info').mkdir(parents=True)
            (root/'tmp').mkdir()
            (root/'usr/lib/opkg/info/kernel.list').write_text('')
            status = root/'usr/lib/opkg/status'
            status.write_text('Package: kernel\nVersion: '+abi+
                              '\nArchitecture: aarch64_cortex-a53\nStatus: install ok installed\n\n')
            original = status.read_bytes()
            verify = work/'verify'
            # Same compressed-or-plain input handling as OpenWrt opkg-key.
            verify.write_text('#!/bin/sh\n[ "$1" = verify ] || exit 1\n'
                '(zcat "$3" 2>/dev/null || cat "$3") | '+shlex.quote(str(tools/'usign'))+
                ' -V -x "$2" -m - -p '+shlex.quote(str(feed/'feed-key.pub'))+'\n')
            verify.chmod(0o700)
            config = work/'opkg.conf'
            config.write_text('dest root /\nlists_dir ext /var/opkg-lists\n'
                'arch all 1\narch noarch 1\narch aarch64_cortex-a53 10\n'
                'option check_signature\nsrc/gz recs06_release '+url+'\n')
            command = [str(tools/'opkg'), '-f', str(config), '-o', str(root),
                       '--verify-program', str(verify)]
            operations = [['update'], ['--noaction', 'install', 'luci-app-sqm'],
                          ['--noaction', 'install', 'kmod-fs-exfat']]
            for args in operations:
                result = subprocess.run(command+args, capture_output=True, timeout=180)
                output = result.stdout+result.stderr
                log.extend(output)
                if result.returncode or b'Signature check failed' in output:
                    raise ValueError(output.decode(errors='replace')[-3000:])
                if args == ['update'] and b'Signature check passed' not in output:
                    raise ValueError('opkg did not confirm signature verification')
                if status.read_bytes() != original:
                    raise ValueError('Dry run unexpectedly changed package status')
            return dict(kernel_abi=abi, url=url, signed_update=True,
                        sqm_dependency_dry_run=True, exfat_dependency_dry_run=True,
                        packages_installed=False, router_tested=False), bytes(log)
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('feed', type=Path)
    parser.add_argument('--url')
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    report, output = test_feed(args.source, args.feed, args.url)
    if args.log:
        args.log.write_bytes(output)
    print(json.dumps(report))
