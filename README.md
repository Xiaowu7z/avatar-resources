# avatar-resources · JARVIS资源仓库

用于保存JARVIS的资源目录、版本清单、许可和维护说明。大型模型 ZIP 放在 **GitHub Releases**，主分支不存模型权重。小 APK 保留应用逻辑、运行时和可信文件清单；资源下载或导入一次后留在手机，覆盖更新 APK 可继续复用。

实际仓库：[Xiaowu7z/avatar-resources](https://github.com/Xiaowu7z/avatar-resources)。资源使用固定 Release 标签 `models-v1`；下载地址和哈希见 [catalog-v1.json](catalog-v1.json)。**models-v1 已发布。** [Release 页面](https://github.com/Xiaowu7z/avatar-resources/releases/tag/models-v1) 已提供两份 ZIP、许可和目录快照。构建提交为 [`aa752baa5b84`](https://github.com/Xiaowu7z/avatar-resources/commit/aa752baa5b84aba05b3ee10db98b957f1f1894c2)，[发布工作流](https://github.com/Xiaowu7z/avatar-resources/actions/runs/34218405579) 全部步骤通过。

## 已有资源

| 资源 | 用途 | ZIP 字节数 | 解压后字节数 | 资源版本 |
| --- | --- | ---: | ---: | --- |
| `JARVIS-asr-paraformer-v1.zip` | 普通话流式识别 | 218651054 | 237202501 | `paraformer-v1` |
| `JARVIS-wake-zh-int8-v1.zip` | “JARVIS”本地唤醒 | 3698001 | 5025632 | `zh-int8-v1` |

两包都是现有文件的真实清单，归档与内部文件 SHA-256 保存在模板和 `manifests/` 中。识别模型也具备英语能力，JARVIS当前交互范围以普通话为主。当前配套运行时为 `sherpa-onnx 1.13.7`，App 为 `com.wuge.xiaowu 0.2.1`，Android 11/API 30 及以上、ARM64；这里描述配套代码的兼容目标，并不表示已经完成所有真机验证。

**目前没有独立 TTS 声音包。** JARVIS的播报音色来自手机已经安装的离线语音引擎。仓库不包含微软语音权重，也没有“贾维斯原声”权重；沉稳效果目前通过用户试听选音色、调整语速和音调实现。

## 下载和可复现发布

- [普通话识别资源 ZIP](https://github.com/Xiaowu7z/avatar-resources/releases/download/models-v1/JARVIS-asr-paraformer-v1.zip)
- [中文唤醒资源 ZIP](https://github.com/Xiaowu7z/avatar-resources/releases/download/models-v1/JARVIS-wake-zh-int8-v1.zip)
- [目录快照](https://github.com/Xiaowu7z/avatar-resources/releases/download/models-v1/catalog-v1.json)
- [来源与许可](https://github.com/Xiaowu7z/avatar-resources/releases/download/models-v1/resource-packs-LICENSE.txt)

`Reproduce and publish models-v1` 工作流已完成首次发布。它从固定 Hugging Face 提交下载 ASR 文件，从官方固定 URL 下载 KWS 归档，先验证源文件，再以固定路径、时间戳和 Unix 文件属性生成 ZIP。完整 ZIP 的大小、SHA-256 和每个内部文件必须与现有清单完全一致，才能上传为草稿并公开。

本地可复现，不需要任何 API 密钥：

```bash
/usr/bin/python3 tools/build_resources.py
python3 tools/catalog.py validate catalog-v1.json --archives dist
```

已验证 Python 3.12.3/zlib 1.3 与 Python 3.12.13/zlib 1.3.2 生成逐字节相同的两份 ZIP。工作流使用 Ubuntu 24.04 的系统 Python；如果将来压缩器行为变化导致归档哈希不同，发布会停止，不能用新哈希悄悄覆盖此固定版本。

工作流发布仅使用本仓库 GitHub Actions 的 `GITHUB_TOKEN`、`contents: write` 权限，不需要保存个人 Token。已公开的 `models-v1` 不会被重复运行覆盖；同一提交未完成的草稿可以重新运行继续上传。`templates/catalog-v1.json` 保留空地址模板，已配置目录在根目录。

## App 如何使用

当前 v0.2 的资源入口支持**手动导入 ZIP，或粘贴 HTTPS ZIP 地址下载**，还没有自动浏览远程目录的功能。因此现阶段把目录中某个 `download_url` 复制到 App 即可；不能把 `catalog-v1.json` 的地址当作资源 ZIP 地址。

App 对解压路径、文件大小、完整性和 SHA-256 进行检查，信任依据是 APK 中内置的模型清单。目录里的归档 SHA-256 另供发布校验和未来下载器使用。远程目录本身不能修改 App 接受的模型，也不能替代代码中的校验。

安装先在临时目录校验完整资源，再逐包通过同一文件系统内的目录重命名替换，保留恢复备份以处理安装中断。这是**每个资源包**的原子切换，不是 ASR 和 KWS 两包同时切换的整组事务。已存在且哈希相同的版本直接复用；覆盖更新 APK 不必重新下载，卸载或清除应用数据后需要重新导入。

未来增加其他识别模型、唤醒模型或自带 TTS 声音时，需要先实现对应运行时、文件结构、配置和兼容验证，再发布新的资源及 App 清单。不能把任意 ONNX/GGUF/语音权重放进 Releases 就让当前 App 自动使用。

自定义中文唤醒词的配置与拼音数据由配套 APK 处理，当前两份资源 ZIP 保持原样。KWS 包中的默认关键词仍为“贾维斯”，不要为了改唤醒词而修改本资源包的固定文件和哈希。

## 版本与维护

- `catalog_schema_version: 1` 定义目录字段；不兼容地修改字段语义时升级此版本。
- `resource_pack_format_version: 1` 对应本批 ZIP 的白名单路径格式。
- 每个模型有独立 `version`、配套运行时、App 兼容范围及内部文件清单。目录版本、资源版本、App 版本不是同一个数字。
- 发布后的固定标签和 ZIP 必须作为不可变版本维护。内容变化就创建新版本、文件名和标签，保留旧文件供旧 APK 继续下载。不要原地覆盖同名文件或移动旧标签；本模板提供的是维护约定，并未代替你启用任何平台设置。
- 新旧目录并存时保留稳定入口，同时让发布快照固定到具体标签或提交。客户端将来接目录时仍需保留兼容筛选和本地缓存。

来源和许可证见 [NOTICE.md](NOTICE.md)、[licenses/resource-packs-LICENSE.txt](licenses/resource-packs-LICENSE.txt)。发布前核对事项见 [MAINTAINING.md](MAINTAINING.md)。
