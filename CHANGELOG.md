# Change Log

本文件记录每次推送到 GitHub 的功能、行为、规则和重要修复。当前项目不使用正式版本号，因此用日期和简短主题组织记录。

## 维护规则

1. 每次准备 push 新变更前更新本文件；一次 push 可以概括多个 commit。
2. 标题使用 `YYYY-MM-DD — 简短主题`。
3. 按需使用 `Added`、`Changed`、`Fixed`、`Removed` 或 `Security`；空分类不保留。
4. 描述能力、行为和用户结果，不写成文件名清单。
5. Change Log 与对应代码、规则或文档在同一批 push 中提交。

## 2026-08-07 — Fingerprint authority and language integration

### Changed

- Hard pass/fail policy now has one machine-readable authority, while account fingerprints focus on distinct voice realization: R1 uses practical working judgments and implementation lessons; R2 uses production skepticism, workload limits, and decision criteria.
- First-person openings, language buffers, and the required technical category example now have account-specific placement guidance, reducing repetitive title/opening templates and standalone product-name sentences.
- The first sentence must now establish first-person perspective, and every body must contain at least one grammatical language buffer tied to a judgment or uncertainty. Missing either blocks validation; buffers cannot soften source facts, benchmark setup, or measurements.

### Fixed

- Validation now rejects assigning one account the other account's known fingerprint instead of accepting any recognized fingerprint ID.
- The prohibited-brand check now also covers generated review metadata such as `angle`, not only title, body, disclosure, and mention basis.
- Opening and language-buffer checks now fail closed instead of producing advisory warnings, including when first person appears only after the first sentence.

## 2026-08-07 — First-person or question titles and indirect Milvus context

### Changed

- Reddit 标题现在必须使用第一人称单数视角，例如 `I think`、`Now I believe` 或 `What I learned`，或者写成以 `?` 结尾的明确疑问句；完全第三人称的陈述标题会阻断验证。
- 每篇正文仍必须恰好出现一次有来源依据的 Milvus，但必须放在同类技术举例或并列语境中，例如 `vector databases like Milvus`、`data infrastructures such as Milvus` 或 `Milvus and other databases`；直接产品植入会阻断验证。

### Added

- 增加标题视角、自然 Milvus 上下文、直接植入拒绝和合法同类并列写法的回归测试。

## 2026-08-06 — Required Milvus body mention

### Changed

- 每篇 Reddit 草稿正文现在必须恰好出现一次有来源依据的 Milvus，并填写 `milvus_mention_basis`；正文零次或超过一次都会阻断验证和飞书写入。
- 标题继续完全禁止 Milvus，所有生成内容继续禁止 Zilliz；无法支持一次 Milvus mention 的来源必须被替换，不能补写无依据的品牌内容。
- 随仓库提供的四槽 validation sample 已同步新合同，README 中的标准校验命令可直接通过；当前 live Base 缺少专用 basis 字段时，依据继续保存在 pack JSON 中。

### Added

- 增加正文零次和两次 Milvus 都失败、正文恰好一次通过的回归测试。

## 2026-08-06 — First-person openings and Post Type closings

### Changed

- Reddit 草稿现在在首段立即建立匿名第一人称视角，不再到后续段落才出现账号声音；第一人称仍必须有来源支持，不能补写个人经历。
- 判断和不确定性会加入少量自然 language buffers，例如 `probably`、`one concern I have`、`my current view` 或 `I would likely`；来源支持的事实和指标仍保持直接表达。
- `Tutorial` 以结论、验证步骤或下一步收尾，不再追加社区问题；`Discussion` 如需邀请互动，改用 `Would love to hear your thoughts.` 一类柔和表达，避免生硬的问句结尾。

### Added

- Draft validation 会拒绝以问题结尾的 `Tutorial`，并提示缺少首段第一人称、缺少自然 language buffer，或以强问句结尾的 `Discussion`。

## 2026-08-04 — Recent-source priority for weekly packs

### Changed

- Weekly Reddit 选题现在优先使用最近 7 天内发布、技术适配且尚未生成的官方 Blog；如果近期来源不能覆盖四个固定槽位，才按发布日期从新到旧使用更早来源补齐。
- Pool sync 与 screening 输出会按来源发布日期排序并标记近期优先候选，使 `--limit` 和人工选题都先处理最新内容。

### Fixed

- Feishu Review 写入现在会在创建文档前把来源发布日期转换为 Date 字段要求的毫秒时间戳，避免文档创建后因日期格式错误导致 Base 记录失败。
- 失败恢复可以复用已经创建的 Content Doc，避免重试 weekly delivery 时产生重复文档。

### Added

- 新增最近 7 天优先规则和回归测试，防止 weekly workflow 重新退化为无日期顺序的候选选择。

## 2026-08-03 — Offline Reddit JSON Content parsing

### Added

- 新增 `$reddit-json-content-parse`：只读取人工粘贴到飞书 `Reddit JSON Content` 的完整 JSON，预览并回写互动指标、帖子状态、评论摘要、舆情预警和 Milvus 信号。
- 解析预览会绑定记录集合、字段计划和每条 JSON 内容的 SHA-256；正式写入前若内容或表结构变化会拒绝执行。

### Changed

- 发布后流程改为完全离线解析。空 JSON 内容行显示为等待粘贴，不作为失败，也不会访问 Reddit 或覆盖 `Reddit JSON` / `Reddit JSON Content`。
- 任意检测到的负面评论至少触发 `Watch`；重复或更强的负面讨论可升级为 `Alert`。

### Removed

- 退役会访问 Reddit `.json` 端点的 `$reddit-post-monitor` 及 URL 生成流程，当前仓库只保留人工复制 JSON 后的解析 Skill。

## 2026-08-03 — Published Reddit post monitoring

### Added

- 新增 `$reddit-post-monitor`，可通过已发布帖子的公开 `.json` 端点预览 upvotes、评论数、估算 downvotes、upvote ratio 和帖子状态，并在明确授权后写回 Reddit Persona Pipeline。
- 新增评论摘要、`Public Opinion Alert` 和多值 `Milvus Signal`，支持识别负面讨论、Milvus 问题/对比/采用意向及 Zilliz mention，同时不把 Reddit 用户名写入飞书。
- 新增本地 URL JSON 输入、浏览器保存 JSON fallback 和人工分析覆盖文件，允许在 Reddit 对命令行客户端返回 403/429 时继续只读处理，并在 live write 前复核自动评论归纳与信号判断。
- 新增带 digest 的 preview snapshot；live write 只能消费已复核快照，若飞书目标行或字段计划发生变化就拒绝写入。

### Changed

- 发布后状态现在区分 Active、Removed、Deleted、Locked、Archived 和 Unavailable；只有成功确认 Removed/Deleted 时才把原有 `Status` 更新为 `Cancel`。
- Downvote 字段明确标为 `Downvotes (Estimated)`，避免把 Reddit 未公开的精确 downvote 数量误报为真实指标。
- Reddit share link 会先解析到 canonical submission URL；非 HTTPS、非帖子路径和本地输入触发的 live write 会被拒绝，删除作者账号也不再被误判为帖子删除。
- 自动摘要只输出聚合主题和情绪计数，不把原始评论片段写入飞书；评论样本默认关闭，只能显式开启用于本地复核。

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
