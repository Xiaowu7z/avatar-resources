#!/usr/bin/env python3
"""Validate local immutable resource metadata and fill real GitHub release URLs. No network."""
import argparse
import copy
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "catalog-v1.json"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
KINDS = {"asr": "speech_recognition", "kws": "keyword_spotting"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "JSON 存在重复键：" + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def repo_url(value):
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.netloc == "github.com"
            and not parsed.query and not parsed.fragment, "仓库地址必须为实际 GitHub HTTPS 仓库地址")
    pieces = parsed.path.strip("/").split("/")
    require(len(pieces) == 2 and all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in pieces),
            "仓库地址格式应为 github.com/所有者/仓库名")
    require(all(p not in {".", ".."} for p in pieces), "仓库路径无效")
    require(not pieces[1].endswith(".git"), "请填写浏览器中的仓库地址，去掉 .git 克隆后缀")
    return "https://github.com/" + "/".join(pieces)


def release_tag(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value),
            "固定标签仅使用字母、数字、点、下划线和短横线")
    require(value.lower() not in {"latest", "main", "master", "nightly", "snapshot"},
            "请使用固定资源版本标签，不能使用 latest/main/nightly 等浮动名称")
    return value


def asset_url(repo, tag, filename):
    return repo + "/releases/download/" + quote(tag, safe="") + "/" + quote(filename, safe="")


def digest(stream, limit=None):
    hasher, size = hashlib.sha256(), 0
    while True:
        block = stream.read(1024 * 1024)
        if not block:
            break
        size += len(block)
        require(limit is None or size <= limit, "文件解压大小超过清单")
        hasher.update(block)
    return size, hasher.hexdigest()


def validate_archive(path, pack):
    require(path.is_file(), "找不到资源包：" + str(path))
    require(path.stat().st_size == pack["bytes"], "ZIP 大小不符：" + path.name)
    with path.open("rb") as stream:
        size, hashed = digest(stream, pack["bytes"])
    require(hashed == pack["sha256"] and size == pack["bytes"], "ZIP SHA-256 不符：" + path.name)
    expected = {entry["path"]: entry for entry in pack["files"]}
    allowed_dirs = {"asr/", "asr/paraformer/"} if pack["id"] == "asr" else {"kws/"}
    seen, actual = set(), set()
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            name = entry.filename
            require(name not in seen, "ZIP 存在重复路径：" + name)
            seen.add(name)
            if entry.is_dir():
                require(name in allowed_dirs and entry.file_size == 0, "ZIP 目录不在白名单：" + name)
                continue
            require(name in expected, "ZIP 包含清单外文件：" + name)
            require(not entry.flag_bits & 1, "不接受加密 ZIP")
            item = expected[name]
            require(entry.file_size == item["bytes"], "ZIP 内文件大小不符：" + name)
            with archive.open(entry) as stream:
                size, hashed = digest(stream, item["bytes"])
            require(size == item["bytes"] and hashed == item["sha256"], "ZIP 内文件校验失败：" + name)
            actual.add(name)
    require(actual == set(expected), "ZIP 缺少必要文件：" + path.name)


def validate(data, allow_template=False, archives=None):
    require(isinstance(data, dict), "目录必须是 JSON 对象")
    require(data.get("catalog_schema_version") == 1, "不支持的目录 schema 版本")
    require(data.get("resource_pack_format_version") == 1, "不支持的资源包格式版本")
    require(data.get("application", {}).get("package") == "com.wuge.xiaowu", "App 包名不符")
    require(data["application"].get("known_compatible_versions") == ["0.2.0"],
            "此模板只记录已适配的 App 0.2.0，其他版本需重新审阅兼容性")
    repository, tag = data.get("repository_url"), data.get("release_tag")
    blank = repository == "" and tag == ""
    require(not blank or allow_template, "目录尚未配置真实仓库和固定 Release 标签")
    if not blank:
        require(repository == repo_url(repository), "仓库地址须使用规范格式")
        release_tag(tag)
    require(data.get("license_file") == "licenses/resource-packs-LICENSE.txt", "许可文件路径不符")
    expected_license_url = "" if blank else asset_url(repository, tag, "resource-packs-LICENSE.txt")
    require(data.get("license_download_url") == expected_license_url, "Release 许可链接不符")
    packs = data.get("packs")
    require(isinstance(packs, list) and len(packs) == 2, "本模板必须且仅包含已适配的 ASR、KWS 两包")
    release_manifest = read_json(ROOT / "manifests" / "resource-packs-v1.json")
    require(release_manifest.get("format_version") == 1, "归档清单格式不符")
    original_packs = {entry["id"]: entry for entry in release_manifest["packs"]}
    seen = set()
    for pack in packs:
        require(isinstance(pack, dict), "资源条目必须是 JSON 对象")
        ident = pack.get("id")
        require(ident in KINDS and ident not in seen, "资源 ID 不支持或重复")
        seen.add(ident)
        require(ident in original_packs, "归档清单缺少资源：" + ident)
        for field in ("version", "archive", "bytes", "sha256", "payload_bytes"):
            require(pack.get(field) == original_packs[ident].get(field), "目录与原始归档清单不一致：" + ident + "." + field)
        require(pack.get("kind") == KINDS[ident], "资源用途不符")
        require(pack.get("license") == "Apache-2.0", "资源许可不符")
        require(pack.get("runtime", {}).get("name") == "sherpa-onnx"
                and pack["runtime"].get("version") == "1.13.7", "模型运行时不符")
        require(isinstance(pack.get("version"), str) and pack["version"], "缺少资源版本")
        filename = pack.get("archive")
        require(isinstance(filename, str) and re.fullmatch(r"[A-Za-z0-9_.-]+\.zip", filename), "归档文件名无效")
        require(isinstance(pack.get("bytes"), int) and 0 < pack["bytes"] <= 320 * 1024 * 1024, "归档大小无效")
        require(isinstance(pack.get("sha256"), str) and SHA256.fullmatch(pack["sha256"]), "归档 SHA-256 无效")
        expected_url = "" if blank else asset_url(repository, tag, filename)
        require(pack.get("download_url") == expected_url, "资源下载地址必须固定到此 Release 的同名文件")
        manifest_ref = pack.get("manifest")
        require(manifest_ref == "manifests/" + ident + "-manifest.json", "内部文件清单引用无效")
        manifest = read_json(ROOT / manifest_ref)
        prefix = "asr/paraformer/" if ident == "asr" else "kws/"
        expected_files = [{"path": prefix + item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                          for item in manifest["files"]]
        require(pack.get("files") == expected_files, "目录与归档内部文件清单不一致：" + ident)
        require(pack.get("payload_bytes") == sum(item["bytes"] for item in expected_files), "解压后大小不符")
        if archives is not None:
            validate_archive(Path(archives) / filename, pack)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="校验目录及可选的本地资源 ZIP")
    check.add_argument("catalog", type=Path)
    check.add_argument("--allow-template", action="store_true")
    check.add_argument("--archives", type=Path)
    generate = sub.add_parser("generate", help="校验本地 ZIP 后填入实际仓库地址，不上传")
    generate.add_argument("--repo-url", required=True)
    generate.add_argument("--release-tag", required=True)
    generate.add_argument("--archives", type=Path, required=True)
    generate.add_argument("--output", type=Path, default=ROOT / "catalog-v1.json")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate(read_json(args.catalog), args.allow_template, args.archives)
            print("校验通过：" + str(args.catalog))
        else:
            data = copy.deepcopy(validate(read_json(TEMPLATE), True, args.archives))
            repository, tag = repo_url(args.repo_url), release_tag(args.release_tag)
            data["repository_url"], data["release_tag"] = repository, tag
            data["license_download_url"] = asset_url(repository, tag, "resource-packs-LICENSE.txt")
            for pack in data["packs"]:
                pack["download_url"] = asset_url(repository, tag, pack["archive"])
            validate(data)
            require(args.output.resolve() != TEMPLATE.resolve(), "请保留空地址模板，不要覆盖 templates/catalog-v1.json")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("已生成：" + str(args.output) + "（仅本地生成，尚未上传）")
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print("校验失败：" + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
