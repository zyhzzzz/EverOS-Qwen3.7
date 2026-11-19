# Qwen3.7-Flash + OpenClaw + EverOS 复现实验审查材料

本仓库记录两次独立的 EvoAgentBench Information Retrieval / Web Research 实验。目标是让审查者追溯实际代码、数据使用、配置、结果和偏差，并按相同方法重新运行。

**结论边界：基于固定官方代码的 EverOS 方法复现，包含模型替换、本地模型服务封装和最终答案提取适配；不是所有条件与历史排行榜完全一致的原样复刻。**

## 实际结果

| 实验 | Train | Skill 数 | Baseline | EverOS | 增益 |
| --- | --- | --- | --- | --- | --- |
| Run 1 | 77/154，50.00% | 17 | 23/65，35.38% | 29/65，44.62% | +9.23个百分点 |
| Run 2 | 78/154，50.65% | 20 | 22/65，33.85% | 29/65，44.62% | +10.77个百分点 |

每次均独立训练、提取、测试，`trials=1`，不是对同一套 skill 连跑两遍测试。两次 EverOS 同分，但8题对错变化；baseline 有13题变化。只能说总体准确率接近，不能据此断言稳定或显著提升。

Run 1、Run 2 分别对应原实验目录日期 `20261117`、`20261118`，目录日期不是所有任务的精确完成时间。旧自建 loop、DeepSeek 作答实验和其他预算实验均不属于本材料。

## 阅读顺序

1. [实验方法与配置](docs/METHOD.md)：模型角色、数据流、skill 与 case 注入、配置差异。
2. [从零部署和运行](docs/REPRODUCE.md)：下载官方源码、数据、索引和模型，配置 API，执行完整流程。
3. [结果及答案审查](docs/RESULTS.md)：逐题统计、接口失败、补评及稳定性解释。
4. [证据与代码导航](docs/AUDIT.md)：实际运行脚本、源码哈希、适配补丁、审查方法与证据不足。
6. [发布包验证记录](docs/VALIDATION.md)：已经执行的检查及尚未验证的事项。

## 官方来源

- [EvoAgentBench 固定版本 benchmark](https://github.com/EverMind-AI/EvoAgentBench/tree/6aa49908adef7d430b3a172d6d7c06d5224ef6d2/benchmark)
- [该版本 EverOS 集成说明](https://github.com/EverMind-AI/EvoAgentBench/blob/6aa49908adef7d430b3a172d6d7c06d5224ef6d2/benchmark/src/skill_evolution/evermemos/README.md)
- [EverOS v1.2.3](https://github.com/EverMind-AI/EverOS/tree/v1.2.3)，commit `48fc9084888bc17100053227284f939a5aca5e91`
- [EvoAgentBench 数据](https://huggingface.co/datasets/EverMind-AI/EvoAgentBench)
- [BrowseComp-Plus 任务](https://huggingface.co/datasets/Tevatron/browsecomp-plus)、[语料](https://huggingface.co/datasets/Tevatron/browsecomp-plus-corpus)、[索引](https://huggingface.co/datasets/Tevatron/browsecomp-plus-indexes)

## 不调用 API 的快速查验

```bash
python scripts/verify_results.py
python scripts/check_release.py
```

`evidence/*_tasks.csv` 公开任务 ID、分数、停止原因、长度和哈希，不包含题干、标准答案、模型回答或思考文本。原始材料保留在私有实验目录；公开分数表可复核统计，但不能代替对原始回答的独立语义审查。

`historical/` 是实际运行脚本的脱敏快照；`scripts/` 中从零部署脚本是在实验结束后整理的可移植版本，不冒充原始运行文件。详见 [代码导航](docs/AUDIT.md)。**新部署脚本尚未在全新机器上重新完成全量付费实验。**