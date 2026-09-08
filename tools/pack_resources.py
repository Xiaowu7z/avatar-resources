#!/usr/bin/env python3
"""Create reproducible, data-only packs accepted by ResourcePacks. No signing files."""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
import zipfile


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def create_pack(assets, output, pack_id, prefix, version, archive):
    manifest = json.loads((assets / prefix / "manifest.json").read_text())
    entries = manifest["files"]
    seen = set()
    for entry in entries:
        name = entry["name"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", name) or name in seen:
            raise ValueError(f"Invalid or duplicate resource filename: {name}")
        seen.add(name)
        path = assets / prefix / name
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"Manifest verification failed: {path}")
    target = output / archive
    temporary = target.with_suffix(".zip.part")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as result:
            for entry in entries:
                # Explicit paths and fixed timestamps; no traversal, manifests, keys, or native code.
                info = zipfile.ZipInfo(f"{prefix}/{entry['name']}", date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                with (assets / prefix / entry["name"]).open("rb") as source, result.open(info, "w") as dest:
                    shutil.copyfileobj(source, dest, 1024 * 1024)
        # Confirm every archive member matches the APK manifest, not merely ZIP CRCs.
        with zipfile.ZipFile(temporary) as result:
            if result.namelist() != [f"{prefix}/{entry['name']}" for entry in entries]:
                raise ValueError("Unexpected archive members")
            for entry in entries:
                sha = hashlib.sha256()
                size = 0
                with result.open(f"{prefix}/{entry['name']}") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        size += len(block)
                        sha.update(block)
                if size != entry["bytes"] or sha.hexdigest() != entry["sha256"]:
                    raise ValueError("Archive round-trip checksum failed")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"id": pack_id, "version": version, "archive": archive, "bytes": target.stat().st_size,
            "sha256": digest(target), "payload_bytes": sum(row["bytes"] for row in entries)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assets = args.project / "app/src/main/assets"
    result = {"format_version": 1, "packs": []}
    for definition in [
        ("asr", "asr/paraformer", "paraformer-v1", "Xiaowu-asr-paraformer-v1.zip"),
        ("kws", "kws", "zh-int8-v1", "Xiaowu-wake-zh-int8-v1.zip"),
    ]:
        pack = create_pack(assets, args.output, *definition)
        result["packs"].append(pack)
        print(json.dumps(pack, ensure_ascii=False), flush=True)
    (args.output / "resource-packs-v1.json").write_text(json.dumps(result, indent=2) + "\n")
    license_text = (assets / "licenses/Apache-2.0.txt").read_text()
    (args.output / "resource-packs-LICENSE.txt").write_text(
        "Xiaowu resource data packs\n\n"
        "ASR: sherpa-onnx-streaming-paraformer-bilingual-zh-en, unmodified INT8 weights.\n"
        "https://huggingface.co/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en\n"
        "KWS: sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01, unmodified INT8 weights.\n"
        "https://github.com/k2-fsa/sherpa-onnx/releases/tag/kws-models\n"
        "The local KWS keyword data selects the phrase Xiao Wu Tong Xue (小五同学).\n"
        "Model licenses: Apache-2.0. Distribute this notice with both resource ZIP files.\n\n"
        + license_text)


if __name__ == "__main__":
    main()
