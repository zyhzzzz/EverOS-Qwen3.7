# Third-party sources and attribution

This review package is not an official EverMind release. It does not redistribute datasets, pretrained weights, private API credentials, or the complete upstream codebases.

| Component | Source/version | Use |
| --- | --- | --- |
| EvoAgentBench | EverMind-AI/EvoAgentBench, 6aa49908adef7d430b3a172d6d7c06d5224ef6d2 | Downloaded runner, adapter, domain tools, extraction and evaluation |
| EverOS | EverMind-AI/EverOS, v1.2.3 / 48fc9084888bc17100053227284f939a5aca5e91 | Downloaded memory service; Apache-2.0 |
| BrowseComp-Plus | texttron/BrowseComp-Plus, upstream reference 046949032b0328319cc9a02663a759ec601d9402 | Dataset/search/judge lineage; see upstream notices |
| Tevatron | texttron/tevatron, dd063104c81a76d6a77c845f667b46b9e5abd625 | Retrieval dependency |
| OpenClaw | openclaw npm package 2026.3.24 | Installed agent scaffold |
| Qwen models | Model repositories linked in docs/REPRODUCE.md | Downloaded local embedding/reranking weights; model-card terms apply |

The answer-selection diff contains context from the EvoAgentBench adapter and explicitly modifies its behavior. Historical supervisor code and model wrappers are experiment integration code, not a substitute implementation of EverOS.

Upstream has a repository-root license and benchmark-specific notices; preserve both rather than assuming one license covers every component. Copies obtained from the pinned EvoAgentBench Git object are included under `licenses/`. Review upstream licensing before redistributing additional files. No new blanket license is asserted for all original materials in this review package.
