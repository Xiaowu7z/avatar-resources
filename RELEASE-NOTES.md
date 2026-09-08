小五同学 0.2.0 的离线识别与唤醒资源，固定版本 `models-v1`。

- `Xiaowu-asr-paraformer-v1.zip`：普通话流式识别资源。
- `Xiaowu-wake-zh-int8-v1.zip`：中文唤醒模型，默认关键词“小五同学”。
- `catalog-v1.json`：固定下载地址、字节数、SHA-256 与内部文件清单。
- `resource-packs-v1.json`：归档 SHA-256 快照。
- `resource-packs-LICENSE.txt`：模型来源与 Apache-2.0 许可。

由仓库 Actions 从官方来源重建，逐文件校验并复现原始 ZIP 的完整 SHA-256 后发布。APK 仍独立校验随应用分发的可信文件清单。

当前没有独立 TTS 声音包。安装后资源留在手机本地，覆盖升级 APK 可继续使用；清除应用数据或卸载后需要重新下载。
