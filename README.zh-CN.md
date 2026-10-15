# Brain Twin

把自己选定的少量笔记整理成经验资料库。提出问题，查看匹配原文；配置模型后，可以获得带来源的回答。分享时明确选择资料，先预览完整内容再导出。

**Alpha · 本地单人使用 · 中英界面 · MIT**

[English](README.md) · [架构与 API](docs/architecture.md) · [安全边界](SECURITY.md)

![深色主题](docs/screenshots/desktop-dark.png)

## 最短启动

需要 Python 3.10 或更新版本。在下载的源码目录中执行：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
brain-twin
```

Windows 使用 `.venv\Scripts\activate` 激活环境。打开 **http://127.0.0.1:5043**。安装后可以在任意目录运行命令，也可使用 `python -m brain_twin.app`。

初次启动自带完全虚构的“Field Notes · 工作札记”。点击“试问：如何记录决定”，再点击“查找依据”。展开来源可查看全文。询问“木星的卫星有多少颗？”会得到明确的资料不足提示。

## 使用流程

1. 在“整理资料库”中编辑名称、描述、风格偏好和来源正文，也可添加、移除来源。点击“保存资料库”后生效。
2. 在“向资料提问”中提出资料覆盖的问题。未保存的改动需先保存。
3. 在“分享档案”中勾选来源、预览共享包、下载 JSON。**共享包包含名称、描述、偏好和所选来源的完整正文**，不包含问答历史或配置的密钥。正文中的秘密不会自动脱敏，必须自行核对。
4. 另一位使用者选择 JSON 文件，预览后导入为新档案；不会覆盖现有档案。

无模型时是诚实的**资料摘录模式**，不冒充生成式分身回答。本版只接受粘贴文本，不抓取网址，不扫描目录，不访问账户。

## 可选模型

在启动前设置环境变量。地址必须是完整的 chat-completions URL：

```sh
export BRAIN_MODEL_URL='http://127.0.0.1:1234/v1/chat/completions'
export BRAIN_MODEL_NAME='your-local-model'
brain-twin
```

远程服务必须使用 HTTPS；本地回环地址允许 HTTP。需要密钥时，通过自己的秘密管理工具向进程注入 `BRAIN_MODEL_KEY`。不要把真实密钥写进源码、笔记、浏览器或共享包。URL 与模型名称必须同时设置；不完整配置会拒绝启动。

模型服务需支持 `response_format: {"type": "json_object"}`，并按[英文说明](README.md#optional-model-answers)返回 `status`、`answer`、`citations`。每条引用必须包含已检索来源 ID 和该摘录中逐字存在的引文。不足时返回 `insufficient` 和空引用列表。错误 JSON、伪造引用、模型错误或超时都会明确失败，不会静默改用摘录模式。

应用只发送问题、风格偏好和最多四段相关摘录。它不发送其他档案或完整资料库。不跟随上游重定向，不将上游错误正文展示给浏览器。本 Alpha 仅使用本地合成 HTTP 服务测试，没有调用真实或付费模型。

## 数据与实际限制

数据默认保存到 `~/.local/share/brain-twin/profiles.json`，可用 `BRAIN_TWIN_DATA_DIR` 修改。采用原子写入和单进程锁；文件损坏时拒绝启动，不覆盖原数据。停止应用后备份该文件。

这是单进程、单人本地工具，没有账户系统、磁盘加密、多进程协调或多人协作。多个标签页可能覆盖彼此的修改。问答只保留在进程内存，任务 15 分钟过期，重启即消失；不写进共享包。

最多 30 个档案、每档案 50 条来源、每条 30,000 字符、每档案来源合计 200,000 字符；问题最多 4,000 字符。检索最多返回四段、每段 900 字符。两个工作线程，最多四个排队或运行任务、保留 64 个结果；满载时返回 503。上游单次 socket 操作超时 25 秒，响应最多 128 KiB。

中文采用双字词片段、英文采用词项匹配。它不理解语义，可能漏掉同义词或匹配到错误段落。**引用有效只证明来源 ID 和引文真实存在，不保证模型结论语义正确。** 原文中的提示注入也不能保证完全抵抗。依赖回答前，请核对全文。资料运行中被修改时任务会失败，要求重新提问。

`brain-twin --port 5053` 可修改端口。始终只绑定 `127.0.0.1`，不要把开发服务器公开到互联网。

## 验证与开发

```sh
python -m pip install '.[test]'
python -m pytest
python -m pip install build
python -m build
```

覆盖中文命中、无关拒答、增删改、持久化、分享选择和往返、CSRF/Origin/Host、防 XSS、任务上限、实际模型请求字段、伪造引用、模型错误、重定向拒绝、两主题对比度。测试的 HTTP 服务只绑定本地回环地址。CI 使用 Python 3.10 和 3.14，并构建 wheel。

浏览器主流程验证：

```sh
python -m pip install playwright
python -m playwright install chromium
python scripts/browser_smoke.py
```

`/styleguide` 展示真实双主题组件；[截图目录](docs/screenshots)包含桌面、手机和分享预览。无需前端构建，不加载 CDN、第三方字体或分析脚本。
