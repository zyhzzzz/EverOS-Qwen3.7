# 审查者导航与证据边界

## 1. 先核对什么

| 问题 | 对应材料 |
| --- | --- |
| 是否实际调用原生 OpenClaw | `historical/run1/qwen_everos_flow.py` 中 command/provider；官方 adapter 路径及哈希 |
| 是否实际运行 EverOS | 同一脚本的 everos init/server、官方 extract/eval 命令 |
| 代码是否额外改过 | `evidence/source_audit.json` 与 `historical/run1/answer-selection.diff` |
| 两次配置是否一致 | `evidence/run1_manifest.json`、`run2_manifest.json`、监督脚本原始哈希 |
| 成绩是否能重算 | `evidence/run1_tasks.csv`、`run2_tasks.csv`，运行 `scripts/verify_results.py` |
| 是否删除失败题 | CSV 的完整ID集合、停止原因及 `content_filter_error`，分母保持65 |
| skill 是否来自测试能力标签 | 官方 eval 的 API query 路径、`--top-k 2`，没有使用静态按簇路径 |
| 是否全部注入 | 通过 API 检索；默认也包括 case，不是纯 skill 消融 |
| 第二次为什么有恢复脚本 | `historical/run2/resume_qwen_repeat.py` 和 `evidence/run2_judge_repair.json` |

## 2. 代码分层

### 实际运行快照：historical

保存实际服务器文件的脱敏副本，不根据新结论改写历史方法。绝对个人路径换成 `/home/REDACTED`；这是审阅代码，不是可直接在新机器运行的入口。

`evidence/source_hashes.json` 保存脱敏前原文件 SHA256，所以包含路径替换的文件可能与其原始哈希不一致。发布包自身的逐文件哈希见 `SHA256SUMS.json`，两个哈希用途不同。

### 可移植整理版：scripts

- `bootstrap.sh`：获取固定官方代码、隔离安装依赖及 OpenClaw。
- `download_assets.py`：官方解密/索引准备、语料及模型下载、split检查。
- `prepare_run.py`：建立新 run、复制代码、应用补丁。
- `flow_template.py`：由 Run 1 实际监督脚本参数化路径而来，核心阶段和参数不变。
- `start_official_local_search.py`、`everos_local_models.py`：历史本地服务包装器的路径参数化副本。
- `apply_answer_patch.py`：同样的补丁，移除对私有历史题的测试依赖，改用合成正负例。
- `verify_results.py`：重算脱敏结果。
- `audit_run.py`：对复现者自己的运行目录执行只读结构审查，不输出题答正文。
- `check_release.py`：语法、敏感文件、文本模式、Markdown 链接和发布文件哈希检查。

这套材料不重复打包整个官方源码；复现代码少，是因为运行时下载固定官方仓库，不是用几行代码取代 EverOS。

## 3. 固定源码比对

本次审阅将服务器 benchmark 的38个 Python 文件与本地 Git 对象中 commit `6aa49908adef7d430b3a172d6d7c06d5224ef6d2` 的对应内容比较，仅 adapter 不同。将服务器 EverOS 的301个 Python 文件与本地 v1.2.3 源码归档比较，未发现差异。相关逐文件 SHA256 已公开。

补丁前 adapter SHA256：

`cc50b709ae3a6027b25bc32fa2ead49ea9c16015cd2ae2a060aa0863edfe4aca`

补丁后：

`1aa4d7537868fff345a8bf4a1fc061d8abf2acada86cdd414a39854ab01bbf42`

这不等于原机器全部状态的密码学证明：未完整冻结 npm 依赖树、HF快照、提供商内部模型权重或每个请求的服务端有效参数。源码比对也不是对所有安全/方法问题的完整证明。

## 4. 已知差异和不足

1. 模型角色与历史排行榜不同，不能以该结果直接验证原排行榜增益。
2. 最终答案提取不是官方 adapter 原样实现。修改同时作用于两组，但仍会影响评分。
3. embedding/reranker 通过自建 Transformers HTTP 包装器运行，非托管推理服务原样复现。
4. 每次 trials=1，仅两个端到端重复；统计证据有限。
5. 存在 API 内容审查失败与一次 judge 格式补评，已全部计入并披露。
6. Skill 稳定指纹不严格证明异步任务队列已全部排空；本次未额外冻结服务。
7. 记忆推理默认参数与作答 high 不是同一件事；不能把作答预算当作提取预算。

## 5. 受控原始审查流程

需要进一步审查时，先约定数据使用范围与访问方式，再在私有环境按任务 ID 打开对应会话和 judge 记录。确认其 SHA256 与公开 CSV 一致；检查最终公开回答、judge 提示和响应、API错误、注入缓存。不要要求将完整解密数据贴到公开 issue。

如发现评分错误，应同时保留原分数、复核规则、修改原因和新分数；两组遵循同一规则，不只复核可能提高 EverOS 分数的题。


