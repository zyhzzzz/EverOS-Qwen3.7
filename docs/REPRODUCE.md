# 从零部署到完整实验

这些步骤用于 Linux 单机，两张足够空闲的 GPU，所有服务仅应由受信任用户访问。会下载较大的语料、索引和权重，且完整流程会产生模型 API 费用。先阅读 [方法说明](METHOD.md)。

## 1. 系统准备

准备 Python 3.12、Git、Node.js >=22（应满足固定 OpenClaw 版本的 engines 要求）、npm、Java 21、可用 NVIDIA 驱动以及足够的磁盘/内存。原机器为两张约48GB RTX A6000；启动前执行 `nvidia-smi`，不要抢占其他用户服务的显存。原部署这三个模型服务约占 GPU0 23GB、GPU1 8GB，运行还需余量，不能把这个观察当作最低规格保证。

复制本材料仓库到 `~/openclaw/qwen37-review`，进入该目录。以下命令均从仓库根目录执行：

```bash
export REPRO_ROOT="$HOME/openclaw/qwen37-reproduction"
bash scripts/bootstrap.sh
```

脚本会创建独立目录，执行：

- 下载 `EverMind-AI/EvoAgentBench` 并 checkout `6aa49908adef7d430b3a172d6d7c06d5224ef6d2`，不跟随 main。
- 下载 `EverMind-AI/EverOS` 并 checkout `48fc9084888bc17100053227284f939a5aca5e91`（v1.2.3）。
- 分别建立 benchmark 和 EverOS 的 Python 环境；依赖约束取自实际机器导出的版本记录。
- 安装 `openclaw@2026.3.24` 到独立 npm prefix，不修改个人 OpenClaw 安装。

不方便运行脚本时，可查看 `scripts/bootstrap.sh` 的明确 git/pip/npm 命令。EverOS 核心算法依赖包含 everalgo 包；版本清单在 `evidence/everos-constraints.txt`，不要手写一个 summarizer 来代替。

安装遇到平台依赖冲突应保留日志并报告，不要悄悄升级核心库后仍称相同配置。完整 npm 传递依赖没有冻结为本次原始 lockfile，这是材料的已知缺口。

## 2. 私下配置 API

```bash
cp .env.example "$REPRO_ROOT/.env"
chmod 600 "$REPRO_ROOT/.env"
${EDITOR:-vi} "$REPRO_ROOT/.env"
```

填写作答/提取使用的 DashScope key 和 judge 使用的 DeepSeek key。模型分工见示例，不把 judge 换成 Qwen。文件采用简单 `KEY=value`、不加引号，不添加行内注释；不要把 key 写进命令参数或聊天、截图。

脚本通过 provider 配置调用 OpenClaw，不依赖个人 `~/.openclaw` 中已经保存的账号。独立 HOME 用于隔离个人技能和会话。

## 3. 下载数据、索引和本地模型

```bash
PY="$REPRO_ROOT/runtime/EvoAgentBench-benchmark-6aa4990/.benchmark-venv/bin/python"
"$PY" scripts/download_assets.py
```

该步骤使用固定版本官方工具：

```bash
# 等价的官方数据准备入口；由上面的脚本调用，不必重复执行
cd "$REPRO_ROOT/runtime/EvoAgentBench-benchmark-6aa4990"
.benchmark-venv/bin/python src/utils/browsecomp-plus-tools/setup_data.py \
  --index qwen3-embedding-8b
```

任务来自 [Tevatron/browsecomp-plus](https://huggingface.co/datasets/Tevatron/browsecomp-plus)，索引来自 [Tevatron/browsecomp-plus-indexes](https://huggingface.co/datasets/Tevatron/browsecomp-plus-indexes)。额外下载 [固定语料](https://huggingface.co/datasets/Tevatron/browsecomp-plus-corpus)、[Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B)、[Embedding-4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B)、[Reranker-4B](https://huggingface.co/Qwen/Qwen3-Reranker-4B)，缓存片段 tokenizer。

正式使用的 split 是固定代码中的 `benchmark/data/splits/information_retrieval.json`，不要用不断更新的 HF main split 静默替代。历史 HF split 可从 [EvoAgentBench dataset](https://huggingface.co/datasets/EverMind-AI/EvoAgentBench) 获取做对照，但应比较实际 ID，不只是数量。

下载脚本检查：154/65、无重复、无交集、所有 ID 在任务文件中、8B索引4个分片。解密任务文件 SHA256 与历史值见 `evidence/asset_hashes.json`。下载后若哈希不同，先记录并核对原因，不把新数据悄悄视为相同历史数据。

**历史运行没有完整保存每个 HF 资产的 revision 和全部大文件哈希。** 新脚本为其显式 snapshot 下载记录当前 commit；官方 setup_data 的任务/索引仍沿用其下载方式。这是可追溯性补强，不是对历史 revision 的补造。

## 4. 创建独立实验并核验

回到本材料仓库根目录：

```bash
export EVEROS_MODELS_ROOT="$REPRO_ROOT/assets/models"
"$PY" scripts/prepare_run.py --name run1
```

脚本创建全新目录，复制固定 benchmark，应用答案提取补丁并校验 adapter SHA256。不会开始付费作答。端口19100、19101、19102必须空闲；占用时先查明归属，不要直接杀进程。

建议新机器先做独立的一题连通性验证，确认 search、作答和 judge 都能工作；不要将调试状态或试验性 skill 混入正式 root。历史两次正式实验之前已有单题验证；本包保留最终补丁的正负合成测试，不公开该题正文。

## 5. 运行完整流程

```bash
"$PY" -u "$REPRO_ROOT/runs/run1/qwen_everos_flow.py"
```

长任务建议在已有 `tmux`/`screen` 会话中运行，不要关闭 SSH 后误以为仍在执行。脚本顺序为：

1. 启动固定语料检索、embedding/reranker、全新 EverOS 服务。
2. 官方 runner 收集154条训练轨迹，并检查评分方法。
3. 官方 extractor 提交154条训练轨迹、等待并导出 skill。
4. 官方 runner 跑65条无记忆 baseline。
5. 官方 evaluator 检索注入 skill/case，跑相同65条测试。
6. 记录汇总并停止脚本自己启动的服务；不操作其他服务。

服务配置与监督脚本可审阅 `scripts/flow_template.py`。手动追溯时，其核心命令如下（实际工作目录为各 run 的 benchmark）：

```bash
python src/run.py --agent openclaw --domain information_retrieval \
  --split train --parallel 4 --job train
python src/skill_evolution/evermemos/extract_skills.py \
  --domain information_retrieval --job-dir jobs/train --output-dir ../formal-skills \
  --agent-id formal --project-id formal --app-id qwen37-ir \
  --api-url http://127.0.0.1:19100
python src/run.py --agent openclaw --domain information_retrieval \
  --split test --parallel 4 --job baseline
python src/skill_evolution/evermemos/eval_with_skills.py \
  --domain information_retrieval --split test --parallel 4 --top-k 2 \
  --job with-everos --agent-id formal --project-id formal --app-id qwen37-ir \
  --api-url http://127.0.0.1:19100
```

不要单独运行这些命令却漏掉服务、环境变量或 provider 配置；完整脚本负责准备这些前置条件。

## 6. 查看结果与重复实验

```bash
cat "$REPRO_ROOT/runs/run1/status.json"
tail -n 20 "$REPRO_ROOT/runs/run1/formal-extract.log"
python scripts/audit_run.py "$REPRO_ROOT/runs/run1"
```

每题 `result.json`、`session.jsonl`、`verifier/details.json` 位于 `benchmark/jobs/{train,baseline,with-everos}/{ID}__trial_1/`。`formal-skills/` 为导出记忆，`skill_cache.json` 为测试注入缓存。这些文件只在私有环境保存。

`audit_run.py` 对自己的新实验做只读结构审查，输出分数、最终答案选择一致性、错误类别和会话哈希，不输出题答正文。它不替代语义复判。`verify_results.py` 则专门核对本公开包的两次历史成绩，二者不要混淆。

第一次完成并释放服务端口后，再运行：

```bash
"$PY" scripts/prepare_run.py --name run2
"$PY" -u "$REPRO_ROOT/runs/run2/qwen_everos_flow.py"
```

不要复用 run1 的 EverOS root、训练输出、skill cache 或测试会话。第二次仍重新训练和提取。

如果状态为 `stopped_for_review`，必须查看日志，不是完成。历史 Run 2 在 train 第495题 judge 格式错误后暂停；只补评冻结答案一次，保持判错，再跳过已完成训练恢复。脱敏恢复代码和补评记录已保留在 `historical/run2/`、`evidence/run2_judge_repair.json`。该历史脚本不是任意新实验都可直接执行的通用恢复器。

## 7. 验证范围

本材料的验证包括：源码/补丁哈希检查、Python 语法检查、脚本准备阶段与补丁合成测试、568条公开评分记录重算、安全扫描。未为了发布材料额外在新机器上重新跑完整付费流程。新的 API 可用性、GPU驱动兼容性、网络下载和最终分数需要复现者实际验证。
