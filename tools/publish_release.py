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
# One unpublished bootstrap draft predates the user's JARVIS naming choice.
BOOTSTRAP_DRAFT_COMMIT = '55f173b73c5ec778f0411009bf95578e9c49904c'


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
        if existing['target_commitish'] not in {commit, BOOTSTRAP_DRAFT_COMMIT}:
            raise RuntimeError('Existing draft belongs to a different commit; review it before retrying')
        if existing['target_commitish'] == BOOTSTRAP_DRAFT_COMMIT:
            allowed = {'Xiaowu-asr-paraformer-v1.zip', 'Xiaowu-wake-zh-int8-v1.zip',
                       'resource-packs-LICENSE.txt', 'resource-packs-v1.json', 'catalog-v1.json'}
            if any(asset['name'] not in allowed for asset in existing['assets']):
                raise RuntimeError('Unexpected bootstrap draft asset; review before changing it')
            for asset in existing['assets']:
                gh('api', '-X', 'DELETE', 'repos/' + REPO + '/releases/assets/' + str(asset['id']))
            gh('release', 'edit', TAG, '--repo', REPO, '--target', commit,
               '--title', 'JARVIS Models v1', '--notes-file', str(ROOT / 'RELEASE-NOTES.md'))
    else:
        gh('release', 'create', TAG, '--repo', REPO, '--target', commit, '--draft',
           '--title', 'JARVIS Models v1', '--notes-file', str(ROOT / 'RELEASE-NOTES.md'))
    assets = [output / name for name in [
        'JARVIS-asr-paraformer-v1.zip', 'JARVIS-wake-zh-int8-v1.zip',
        'resource-packs-LICENSE.txt', 'resource-packs-v1.json', 'catalog-v1.json']]
    gh('release', 'upload', TAG, '--repo', REPO, '--clobber', *map(str, assets))
    # Draft replacement is permitted for this exact build only. A published release is immutable.
    # Drafts are not exposed by the public tag endpoint; use the authenticated list.
    releases = json.loads(gh('api', 'repos/' + REPO + '/releases?per_page=100', capture=True))
    metadata = next(item for item in releases if item['tag_name'] == TAG)
    actual = {asset['name']: asset['size'] for asset in metadata['assets']}
    expected = {asset.name: asset.stat().st_size for asset in assets}
    if actual != expected:
        raise RuntimeError('Uploaded release asset names or byte counts differ')
    gh('release', 'edit', TAG, '--repo', REPO, '--draft=false')
    print('Published https://github.com/' + REPO + '/releases/tag/' + TAG)


if __name__ == '__main__':
    main()
