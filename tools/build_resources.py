#!/usr/bin/env python3
"""Fetch official pinned model data, reproduce ZIPs, then fail closed on every hash."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def download(url, target, expected_hash, expected_bytes=None, limit=320 * 1024 * 1024):
    if target.is_file() and sha256(target) == expected_hash:
        if expected_bytes is None or target.stat().st_size == expected_bytes:
            print('Reusing verified source:', target.name, flush=True)
            return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.part')
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Xiaowu-resource-builder/1'})
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open('wb') as output:
                size = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    size += len(block)
                    if size > (expected_bytes if expected_bytes is not None else limit):
                        raise ValueError('Source exceeds expected size')
                    output.write(block)
            if expected_bytes is not None and temporary.stat().st_size != expected_bytes:
                raise ValueError('Source size mismatch')
            if sha256(temporary) != expected_hash:
                raise ValueError('Source SHA-256 mismatch')
            temporary.replace(target)
            print('Verified source:', target.name, target.stat().st_size, expected_hash, flush=True)
            return
        except Exception as error:
            temporary.unlink(missing_ok=True)
            # Redirect locations may be signed. Never include URLs or exception messages.
            print('Source attempt failed:', target.name, attempt, type(error).__name__, flush=True)
            if attempt == 3:
                raise RuntimeError('Could not fetch verified source: ' + target.name) from None
            time.sleep(attempt * 3)


def build(work, output):
    sources = json.loads((ROOT / 'manifests/upstream-sources.json').read_text())
    assets = work / 'project/app/src/main/assets'
    for ident, prefix in [('asr', 'asr/paraformer'), ('kws', 'kws')]:
        destination = assets / prefix
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ('manifests/' + ident + '-manifest.json'), destination / 'manifest.json')
    asr = json.loads((ROOT / 'manifests/asr-manifest.json').read_text())
    for entry in asr['files']:
        source = sources['asr']
        url = source['repository'] + '/resolve/' + source['revision'] + '/' + entry['name']
        download(url, assets / 'asr/paraformer' / entry['name'], entry['sha256'], entry['bytes'])
    kws = sources['kws']
    archive = work / 'source/kws-source.tar.bz2'
    download(kws['url'], archive, kws['sha256'])
    expected = {entry['name']: entry for entry in json.loads((ROOT / 'manifests/kws-manifest.json').read_text())['files']}
    with tarfile.open(archive, 'r:bz2') as source:
        for name, member_name in kws['members'].items():
            member = source.getmember(kws['prefix'] + '/' + member_name)
            if not member.isfile() or member.size != expected[name]['bytes']:
                raise ValueError('Unexpected KWS member: ' + name)
            target = assets / 'kws' / name
            with source.extractfile(member) as data, target.open('wb') as destination:
                shutil.copyfileobj(data, destination, 1024 * 1024)
            if sha256(target) != expected[name]['sha256']:
                raise ValueError('KWS member SHA-256 mismatch: ' + name)
    shutil.copyfile(ROOT / 'resources/kws/keywords.txt', assets / 'kws/keywords.txt')
    (assets / 'licenses').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'licenses/Apache-2.0.txt', assets / 'licenses/Apache-2.0.txt')
    subprocess.run([sys.executable, str(ROOT / 'tools/pack_resources.py'),
                    '--project', str(work / 'project'), '--output', str(output)], check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/catalog.py'), 'validate',
                    str(ROOT / 'catalog-v1.json'), '--archives', str(output)], check=True)
    for name in ['resource-packs-v1.json', 'resource-packs-LICENSE.txt']:
        original = ROOT / ('manifests' if name.endswith('.json') else 'licenses') / name
        if (output / name).read_bytes() != original.read_bytes():
            raise ValueError('Published metadata differs: ' + name)
    shutil.copyfile(ROOT / 'catalog-v1.json', output / 'catalog-v1.json')
    print('All published bytes reproduced exactly.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT / 'build')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.work.resolve(), args.output.resolve())
