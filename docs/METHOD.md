# 方法、环境和配置

## 1. 复现对象

使用 EvoAgentBench commit `6aa49908adef7d430b3a172d6d7c06d5224ef6d2` 的 `information_retrieval` 域。该版本文档将其对应到论文 Web Research；命令行目录仍沿用 Information Retrieval。名称对应不意味着历史榜单、当前榜单和所有方法数值可以直接互换。

运行链路为官方 runner → 官方 OpenClaw adapter（一个公开答案提取补丁）→ OpenClaw 2026.3.24。记忆侧使用 EverOS v1.2.3。

## 2. 数据边界

- 官方划分：154条训练、65条测试，ID 不重叠；不随机换分，不挑选容易题。
- 任务源为 `Tevatron/browsecomp-plus`，通过固定版本官方 `setup_data.py` 下载、解密，仅保存在本地。
- 文档来自固定 BrowseComp-Plus 语料与预建 Qwen3-Embedding-8B 索引。任务是固定语料检索，不是自由联网搜索。
- 训练轨迹送入 EverOS；未指定 `--success-only`，即同时包含成功和失败轨迹。评分信息的处理沿用官方 extractor。
- 测试题用于作答及查询训练侧记忆；测试答案由 verifier 使用。没有专门执行测试轨迹写入 EverOS 的步骤，也没有利用测试成绩选优后汇报。
- 训练和测试的 topic/cluster 标签只用于官方划分。本次 API 检索路径没有按测试能力簇筛 skill；未使用静态 `--skills-dir` 按簇加载路径。

## 3. 模型

| 角色 | 本次设置 |
| --- | --- |
| OpenClaw 作答 | `qwen3.7-flash`，DashScope OpenAI-compatible API |
| EverOS 提取 LLM | `qwen3.7-flash`，通过 `EVEROS_LLM__*` 环境变量指定 |
| 答案 judge | `deepseek-v4-flash` |
| 文档检索 embedding | `Qwen/Qwen3-Embedding-8B` |
| 记忆检索 embedding | `Qwen/Qwen3-Embedding-4B` |
| 记忆重排 | `Qwen/Qwen3-Reranker-4B` |
| 文档片段截断 tokenizer | `Qwen/Qwen3-0.6B`，不是作答或检索 embedding 模型 |

EverOS 的 `everos.toml` 可能仍显示初始化默认 LLM。启动脚本通过环境变量覆盖；该版本配置加载顺序为显式参数 > 环境变量 > root TOML > 默认值。不能只读 TOML 就断定实际提取使用了默认模型。

## 4. 检索与注入

- 文档搜索：FAISS 索引在 CPU，embedding 推理使用 GPU；`k=5`、snippet 最多512 tokens。包装器只注册默认 search，不额外开启 `--get-document`。
- Skill 搜索：官方 `eval_with_skills.py` 调用 EverOS `/api/v2/memory/search`，query 为题目文本，`method=hybrid`、`top_k=2`。
- 默认 `EVAL_INCLUDE_CASES=1`，还会注入返回的相关 case；`CASE_SCORE_THRESHOLD=0.0`，无额外分数阈值过滤。
- 因而准确说法是 **top-k=2 的记忆检索请求，注入返回的 skill 与 case**，不是承诺每题严格仅有两段 skill 文本，也不是仅 skill 的消融实验。
- 每组65题均有非空注入缓存。
- 提取等待规则沿用官方脚本：60秒轮询，默认最多3600秒，非空 skill 指纹连续两次一致可结束。它不是后台全部任务排空的严格证明；未额外加入冻结队列机制。

## 5. 作答、评分与资源预算

| 参数 | 配置 |
| --- | --- |
| 每次 trials / 并行 | 1 / 4 |
| 单题超时 | 3000秒 |
| OpenClaw 推理请求 | `--thinking high`；provider `reasoning=true`、`thinkingFormat=qwen` |
| 模型 contextWindow / maxTokens | 128000 / 96000 |
| 作答温度 | 未显式指定，遵循框架/服务端默认 |
| 自定义最大轮次 | 没有另加40/60轮上限；仍受超时和框架内部行为约束 |
| Judge max_tokens / temperature | 4096 / 0.7 |
| Judge thinking | 官方调用设置 `chat_template_kwargs.enable_thinking=false`；没有 API 侧有效状态的额外测量 |
| 本地 embedding | Transformers，float16，SDPA，单文本推理，截断32768 |
| 本地 reranker | Transformers，float16，SDPA，最长8192，yes/no logits 评分 |

`maxTokens=96000` 是模型配置值，不代表每题实际生成96000 token，也不证明所有请求和提供商都以该值作为有效输出预算。请求预算和实际 usage 必须区分。

原机器：Linux、Python 3.12.7、2张 NVIDIA RTX A6000，驱动535.129.03。查询到两张卡的总显存分别为46068和49140 MiB。共享机器的其他任务不属于本实验。主要安装版本及完整已安装包版本见 `evidence/environment.json` 和 `evidence/source_audit.json`。

## 6. 隔离与变更

两次使用各自的 run 目录、OpenClaw HOME、会话、EverOS root、结果目录。虽然 agent/app/project 字符串相同，但服务数据根不同，不是同一个记忆库。`allowBundled=[]`，工具配置禁止 `group:openclaw`；域配置禁用自由 web_search/web_fetch、exec 等工具，保留固定语料 MCP。

唯一检测到与本地固定版本 benchmark Python 源文件不同的文件为 `src/agents/openclaw/openclaw.py`。对照范围为38个 Python 文件；EverOS 对照301个 Python 文件未发现差异。这不是对所有 npm 传递依赖和机器状态的穷尽证明。

答案提取补丁：只取会话最后一条 assistant 在 `stopReason=stop` 时的公开 text；不取 thinking、不在中间回答里挑正确答案。非正常结束返回空文本，按失败进入评分。两组采用相同规则。

本地 embedding/reranker HTTP 服务是实验方封装，不是原样使用托管服务或 vLLM。`provider=vllm` 在这里用于匹配 rerank API 协议，实际推理后端是 Transformers。这是需要披露的运行环境差异。
