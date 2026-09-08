#!/usr/bin/env python3
"""Publish verified files with gh using only the workflow's repository GITHUB_TOKEN."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'Xiaowu7z/avatar-resources'
TAG = 'models-v1'


def gh(*args, capture=False):
    return subprocess.run(['gh', *args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPO:
        raise RuntimeError('Publishing is restricted to the intended repository')
    commit = os.environ.get('GITHUB_SHA', '')
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise RuntimeError('Missing exact build commit')
    output = ROOT / 'dist'
    subprocess.run([sys.executable, str(ROOT / 'tools/catalog.py'), 'validate',
                    str(ROOT / 'catalog-v1.json'), '--archives', str(output)], check=True)
    releases = json.loads(gh('api', 'repos/' + REPO + '/releases?per_page=100', capture=True))
    existing = next((item for item in releases if item['tag_name'] == TAG), None)
    if existing:
        if not existing['draft']:
            raise RuntimeError('Fixed release is already published; never overwrite assets or tags')
        if existing['target_commitish'] != commit:
            raise RuntimeError('Existing draft belongs to a different commit; review it before retrying')
    else:
        gh('release', 'create', TAG, '--repo', REPO, '--target', commit, '--draft',
           '--title', '小五同学离线资源 models-v1', '--notes-file', str(ROOT / 'RELEASE-NOTES.md'))
    assets = [output / name for name in [
        'Xiaowu-asr-paraformer-v1.zip', 'Xiaowu-wake-zh-int8-v1.zip',
        'resource-packs-LICENSE.txt', 'resource-packs-v1.json', 'catalog-v1.json']]
    gh('release', 'upload', TAG, '--repo', REPO, '--clobber', *map(str, assets))
    # Draft replacement is permitted for this exact build only. A published release is immutable.
    metadata = json.loads(gh('api', 'repos/' + REPO + '/releases/tags/' + TAG, capture=True))
    actual = {asset['name']: asset['size'] for asset in metadata['assets']}
    expected = {asset.name: asset.stat().st_size for asset in assets}
    if actual != expected:
        raise RuntimeError('Uploaded release asset names or byte counts differ')
    gh('release', 'edit', TAG, '--repo', REPO, '--draft=false')
    print('Published https://github.com/' + REPO + '/releases/tag/' + TAG)


if __name__ == '__main__':
    main()
