# 模型来源与许可

本仓库模板仅整理真实已交付的两种数据资源；模型权重本身不存入主分支。

| 资源 | 上游身份 | 许可 |
| --- | --- | --- |
| 普通话流式识别 | `sherpa-onnx-streaming-paraformer-bilingual-zh-en` | Apache-2.0 |
| “JARVIS”唤醒 | `sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01`，INT8 | Apache-2.0 |

识别资源使用上游的 `encoder.int8.onnx`、`decoder.int8.onnx` 与 `tokens.txt`，未修改模型权重。唤醒资源使用上游 INT8 权重和 tokens，并配套本地关键词文件选择“贾维斯”。

归档许可说明与 Apache-2.0 全文保存于 [licenses/resource-packs-LICENSE.txt](licenses/resource-packs-LICENSE.txt)。上游模型卡的交付时副本分别保存在 `licenses/paraformer-model-card.md`、`licenses/kws-model-card.md`。

上游来源（供溯源，本模板生成过程未联网）：

- [Paraformer 模型卡](https://huggingface.co/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en)
- [Paraformer 上游模型](https://www.modelscope.cn/models/damo/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8404-online/summary)
- [KWS 官方发布页](https://github.com/k2-fsa/sherpa-onnx/releases/tag/kws-models)
- [KWS 上游模型卡](https://www.modelscope.cn/models/pkufool/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01)

许可证应与资源一同提供，不要遗漏随 Release 上传的许可文件。此模板没有为微软或电影角色声音声明模型所有权、许可或可下载资源。
