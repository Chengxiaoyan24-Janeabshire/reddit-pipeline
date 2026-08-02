# Change Log

本文件记录每次推送到 GitHub 的功能、行为、规则和重要修复。当前项目不使用正式版本号，因此用日期和简短主题组织记录。

## 维护规则

1. 每次准备 push 新变更前更新本文件；一次 push 可以概括多个 commit。
2. 标题使用 `YYYY-MM-DD — 简短主题`。
3. 按需使用 `Added`、`Changed`、`Fixed`、`Removed` 或 `Security`；空分类不保留。
4. 描述能力、行为和用户结果，不写成文件名清单。
5. Change Log 与对应代码、规则或文档在同一批 push 中提交。

## 2026-08-02 — Knowledge closeout safeguards

### Fixed

- 本地生成的 weekly pack 和 PDF 校验临时文件现在默认不进入 Git，降低审核草稿或中间产物被误推到 GitHub 的风险。
- Reference PDF 交付物与当前 Markdown 规则重新同步，LocalLLaMA 周槽位相关说明不再只停留在可编辑源文件中。
- 回归测试现在会检查每个固定周槽位引用的 Markdown 和截图真实存在，避免规则路径与交付资产再次脱节。

## 2026-07-29 — R2 LocalLLaMA weekly lane

### Changed

- R2 的第二个固定周槽位从 `r/dataengineering` 迁移到 `r/LocalLLaMA`，四槽校验、筛选和飞书审核现在统一使用新渠道。
- LocalLLaMA 槽位按新截图支持 `Discussion`、`Question | Help` 和 `Resources`，同时保留 R2 的匿名、无链接、稳定 persona 和来源依据边界。
- R2 的 topic 匹配扩展到本地模型、自托管推理、量化、硬件适配和本地 RAG，不再推荐退役的 data engineering 槽位。

## 2026-07-24 — Initial cleaned Reddit pipeline

### Added

- 建立 `$reddit-weekly` 路由 Skill 和五个可独立调用的阶段 Skills，支持完整 weekly workflow 或只运行指定阶段。
- 增加 `short_post`，同时保留 `standard_post`、`long_post` 和 `code_long_post`。
- 增加 Published-only sync、开放问题可选、匿名、品牌、无链接和长度档位回归测试。
- 补充项目 README、目录职责、逐步输入输出、JSON 判断规则、冲突决议和 Change Log 维护规范。

### Changed

- Pool sync 固定从 Content All in One / `All content` / `all content` 读取，只接收 `Category = Blog Post` 且 `Status = Published` 的官方 Blog。
- Weekly 内容压缩为 R1/R2 四个固定槽位；两个账号都匿名、空 Disclosure、始终 `no_link`。
- 标题禁止 Milvus；正文允许一次有依据的 Milvus mention；生成内容完全禁止 Zilliz。
- 开放问题从强制结尾改为完全可选，缺少问题不会产生 error 或 warning。
- 项目 runtime 提升到根目录，Skills 统一收进 `.agents/skills/`，不再把 Reddit runtime 包装成独立 Agent 目录。

### Removed

- 移除旧 5–6 账号、warm-up、Medium/calendar sync、local CSV pool/write、subreddit research runtime 和历史 pack 残留。
- 移除已被 README、AGENTS 和机器规则取代的 handoff、账号说明、结构审计和冲突审计副本。
