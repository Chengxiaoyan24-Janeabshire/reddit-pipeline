# 变更日志

本文件记录每次推送到 GitHub 的功能、行为、规则和重要修复。当前项目不使用正式版本号，因此用日期和简短主题组织记录。

## 2026-09-03 — Reddit 原文链接与 James 总结范本

### 新增

- James 每周三篇内容中固定一篇采用“完整总结文章主线、再附原文链接”的结构，并以
  已确认的飞书文章作为非权威风格范本。
- James 账号参考新增可轮换的 Spintax 句式，覆盖身份开场、文章动机、历史转折、
  生产变化、长期含义、原文过渡和反馈收尾；最终稿必须填入来源事实并移除模板标记。

### 变更

- James 仅保留两种改写方式：“总结概括＋原文链接”对同一来源最多生成一次；
  “身份介绍＋自然过渡＋按原文顺序摘写”可用 `part1`、`part2` 等连续改写，直到覆盖全文。
- 只有 James 总结概括模式在 Reddit 正文中单独一段放置原始 `source_url`，并让
  `approved_link` 与其完全一致；James 分段模式和匿名路由继续保持正文无链接。
- Reddit Persona Pipeline 新增“原文”URL 字段；此后每条新审核记录，不论是否为
  James 路由，都在该字段中保留 SyncPost 原始链接。历史稿件和历史审核行不补写。
- James 来源与其他作者统一执行 `2026-01-01` 最早发布日期，不再绕过时间门槛；
  非 James 来源在 `已生成内容数 > 0` 时跳过；James 来源可继续生成尚未覆盖的连续分段，
  但总结概括模式对同一来源仍只允许一次。

## 2026-09-01 — Reddit 爆款标记

### 新增

- Reddit 发布后巡检新增 `爆款是否` 字段预览与历史回填：仅在 Impression、Upvotes、Comments 三项均已有数据时判断，任一项严格大于 3000、5、6 的对应阈值即标记为 `Yes`，缺少任一指标时保持不变。
- 巡检审批快照会绑定用于爆款判断的三项指标及待回填结果；正式写入前数据若变化会要求重新预览。

### 变更

- Reddit 浏览器巡检新增显式历史回检模式，可在用户要求时纳入发布日期超过 14 天或缺少 Publish Date 的 Published 帖子；未来日期仍保持跳过。

## 2026-09-01 — 保留问题标题问号

### 修复

- 创建飞书 Content Doc 时不再把标题中的 `?` 替换成 `-`，问题帖和问句式
  Discussion 的文档标题现在与已校验的 Reddit 标题保持一致。

## 2026-09-01 — 标题工程张力硬校验

### 变更

- 匿名账号标题除第一人称或明确问句外，现在还必须呈现可识别的工程张力：使用
  强反差或反转，或者组合失败归因、时间成本、决策及其代价等信号。普通的主题标签式
  标题和宽泛 `How`、`Where`、`Which` 问句不再通过周包校验。
- 标题 hook 必须受来源事实支持；不得为制造反转或时间成本而虚构运行经历、故障、
  指标或耗时。
- 周包示例改为覆盖反差、错误归因和带代价决策等标题结构，作为起草与校验的可运行
  基准。

## 2026-09-01 — Discussion 问题展开方式

### 变更

- R1、R2 声音指纹新增跨 Subreddit 的 Discussion 展开方式：先表达有限认同和具体
  保留意见，再交代可审查的实现路径、来源支持的证据、最强反方论据与适用边界，
  避免写成宽泛优缺点列表或预设赢家。
- Discussion 现在允许以一到两个可回答的经验问题收尾，重点询问采用、迁移或失效
  阈值；校验只对连续堆叠多个问题发出警告，不再要求统一使用软性邀评句。

## 2026-09-01 — Discussion 开场 Spin

### 变更

- R1、R2 声音指纹新增 Discussion 开场 Spin：根据来源支持的工程张力，在有限认同、
  判断转折、条件式接受、复杂度转移、指标与机制、失效阈值等模式之间选择，不再把
  `I have mixed feelings` 当作固定开场。
- 同一周包不得复用相同开场 scaffold，也不能只替换近义词伪装变化；每个变体必须
  落到真实的系统边界、工作负载或决策标准，并继续禁止虚构个人经历与故障。
- Spin 从开场扩展到整篇 Discussion：必要的推理要素可以重排、合并或通过案例表达，
  并在机制先行、失败先行、证据先行、决策先行等结构之间轮换；句长、段落主语、
  转折方式、bullet 使用和问题数量也不得固定成统一模板。
- 周包校验新增重复 scaffold 拦截；同一匿名周包重复使用 `I have mixed feelings`、
  `The strongest objection`、`This feels reasonable` 等明显模板时直接拒绝交付。

## 2026-08-26 — 新增 R3 James 专属账号

### 新增

- R3 Chapter 模式新增 `partn` 序号：每篇 James 原文独立从 `part1` 开始，后续按
  `part2`、`part3` 连续编号直到章节摘取完成；Direct Share 模式禁止填写该字段。
- 飞书审核表新增 `Source Chapter` 与 `partn` 元数据，方便按来源追踪章节拆分进度。
- 新增 R3 披露作者账号，专门承接 James Luan 来源，并共享 r/Rag、r/AI_Agents、
  r/AIMemory、r/LocalLLaMA 四个现有物理槽位；周包数量仍为四篇，不因共享槽位扩容。
- R3 提供两种互斥改写模式：Chapter 模式一次只处理一个章节级观点并补足独立阅读
  所需上下文；Direct Share 模式概括文章观点、提供原文链接并邀请同行讨论。

### 变更

- James 来源不再分配给 R1/R2，非 James 来源也不会进入 R3。筛选结果会显式返回
  R3 可选改写模式，校验会拒绝账号或模式串路。

## 2026-08-25 — James 独立披露作者编排

### 变更

- James R1 与 R2 现在分别按已交付范本校准：R1 使用身份先行、因果展开的技术解释，
  R2 使用生产问题先行、自然身份桥接、文章观点与同行提问的讨论结构；两种模式不再
  共用笼统的“技术口吻”描述。
- James 范本链接仅作为非权威的语气和段落流证据，运行时风格合同继续由 Guidance
  JSON 定义，账号 Reference 只负责 Persona 落地，避免 Resource 反向成为规则源。
- James Luan 来源会在起草和校验开始时进入独立的披露作者路由，不再继承匿名账号的
  疑问标题、首句 `I`、Buffer words、R2 每周提问配额、Milvus 放置、竞品、品牌、
  匿名或无链接限制。
- James 草稿必须在正文首段以本人语气表明 James、Zilliz CTO 身份；旧的尾部长篇
  身份介绍不再生成。
- R1 改为以 humorous、casual 方式总结和压缩原文观点；R2 改为说明最近撰写了该文、
  在正文直接贴出原文链接、简述主题并欢迎读者意见。
- James 仍然遵守来源事实、安全边界、账号与 Subreddit 槽位、有效 Post Type、社区
  原生结构和风格；运行时会在独立路由配置缺失或退化时 fail closed。
- 路由现在从 Guidance 清单开始，分别连接 James 与 anonymous 的独立 Guidance、
  Reference 和非权威 Resource manifest；账号 Reference 不再把两种身份实现混在同一行。

### 修复

- 修复 James 内容被匿名校验器错误要求疑问句、Buffer words、单次 Milvus 提及或
  间接品牌表达的问题。
- 修复 James 帖开头身份和项目背景不完整的问题：两个账号现在都必须说明 James
  是 Zilliz CTO、Zilliz 是 Milvus 背后的 builder，并介绍 Milvus 是拥有 40K+
  GitHub Stars 的开源向量数据库。
- R1 从 humorous 摘要调整为诚恳、严谨的技术说明，需清楚交代技术背景、概念和
  推理逻辑。James 路由不再强制固定反馈结尾。
- 身份段不再堆叠教育和职业履历，也不再把 GitHub Stars 当作主要技术介绍；现在
  说明 Milvus 如何存储、索引和搜索 embeddings，并自然引出 Vector Lakebase 对
  serving、discovery、治理和持续改进的扩展。R2 在说明文章主题与观点后再放链接。
- R2 改为先提出生产架构模式与运维代价，再自然补充 James/Zilliz 身份，随后说明
  Vector Lakebase 方向和文章观点，最后给出链接并以同行可回答的具体问题收尾。
- James R2 标题统一使用问句，并以 `Love to hear your thoughts on my article.` 收尾；
  该要求只属于 R2，不影响 R1 或 anonymous 路线。

## 2026-08-19 — 收紧匿名口吻与标题风格

### 移除

- 移除此前新增的 DeepSeek 专属起草指南及其在 `guidance/reddit/README.md` 中的登记，
  该指南不再作为独立的 guidance 参考存在。

### 变更

- 账号指纹 reference 禁止使用 `the source`、`the article`、`the blog` 等第三人称
  来源归因表述；博客观点改为以匿名第一人称承载，例如 `I personally`、`my read is`
  或 `I now believe`。
- 标题改为更 dramatic 的对比式写法：优先用相反观察或相互冲突的压力组织标题，
  例如 `The longer an agent runs, the less I care about the prompt`，同时仍满足
  第一人称或疑问句的硬性标题规则。
- 重新生成账号规则审核 Markdown，保持机器 JSON 与人工审核视图一致。

## 维护规则

1. 每次准备 push 新变更前更新本文件；一次 push 可以概括多个 commit。
2. 标题使用 `YYYY-MM-DD — 简短主题`。
3. 按需使用 `新增`、`变更`、`修复`、`移除` 或 `安全`；空分类不保留。
4. 描述能力、行为和用户结果，不写成文件名清单。
5. 变更日志与对应代码、规则或文档在同一批 push 中提交。

## 2026-08-17 — GPT-5.6 版本快照与 README 中文化

### 变更

- 将当前 GPT-5.6 适配后的 weekly pipeline 状态固化为代码快照，并打上
  `gpt-5.6-snapshot` 标签，便于后续在 DeepSeek 专属提示词工作结束后回推。
- 根目录及各分层的 `README.md` 已统一改为简体中文，保持“机器 JSON 是运行时
  权威、生成的 Markdown 只是人工审阅视图、资源文件不定义规则”的说明一致。
- 变更日志继续按简体中文记录用户或运行时结果，不写成逐文件操作清单。

### 新增

- 新增 `gpt-5.6-snapshot` 标签，用于标记 DeepSeek 专属提示词改造前的 GPT
  基线版本。
## 2026-08-17 — R2 每周固定短提问帖

### 变更

- R2 人设现在要求每个 weekly pack 固定生成一篇短提问帖，问题聚焦 Milvus
  使用方式、产品特性或竞品对比，并必须保持有来源支持。
- 该 R2 提问帖使用当前 Subreddit 配置的问题 Post Type：r/AIMemory 使用
  `Open Question`，r/LocalLLaMA 使用 `Question | Help`，长度统一为 `short_post`。
- Workflow 新增 `r2_short_question_policy`，由 `guidance/reddit/workflow/weekly.json`
  作为运行时权威配置；账号人设和 fingerprint 中的对应描述仅作受众角度说明。
- 校验现在会在 weekly 与单 pack 两级强制检查：每包恰好一篇 R2 短提问帖，且该帖
  必须使用 `short_post` 和以 `?` 结尾的疑问标题；不满足时 fail closed。
- 草稿阶段 Skill 明确在保留全局编辑规则的前提下生成这篇固定 R2 短提问帖，
  示例 weekly pack 已同步更新。
- 所有机器规则 JSON 的审核 Markdown 已重新生成，审核视图保持同步。

## 2026-08-17 — 上下游品牌与竞品数据库命名规则

### 新增

- Editorial Guidance 新增品牌命名规则：分析技术栈时可以按来源命名上下游
  技术产品，例如 LangChain、OpenAI、Hermes 或 Claude Code，并保持事实性。
- 数据库竞品名只在问题类帖子中允许点名，当前限定 `Open Question` 和
  `Question | Help`；其他帖子提到别的数据库时使用同类或 peer-group 说法，
  不再只让 Milvus 一个品牌名孤立出现。
- 校验按当前 Post Type 执行该规则，非问题类帖子点名 Pinecone、Qdrant、
  Weaviate、Chroma、pgvector、Elasticsearch 等数据库品牌会失败。
- 新增对应回归测试，覆盖“问题类允许竞品名”和“非问题类拒绝竞品名”两条路径。

## 2026-08-14 — 渐进式资源披露与规则审核层

### 变更

- `asset/` 已统一更名为 `resource/`，截图与生成的 PDF 现在通过 Resource 层提供，
  并继续保持非权威、不能定义规则的边界。
- 不再对 `guidance/`、`reference/` 和 `resource/` 强制排列修改频率；三者都是可按
  业务需要持续变化的内容层。`.agents/skills/` 只保留相对稳定的阶段调用逻辑，
  只有流程阶段、命令、输出或写入门禁变化时才需要调整。
- 运行时资源路径已集中管理，同步、筛选、校验、飞书初始化、PDF 重建和测试不再
  分别硬编码无关目录。
- Workflow 已从 Reference 迁入 `guidance/reddit/workflow/`，Editorial 规则归入
  `guidance/reddit/editorial/`；Reference 现在只保留账号、Subreddit 槽位和受众话题，
  目录职责与 `Guidance` → `Subreddit` → `Audience angle` 的遵循层级一致。
- Subreddit 槽位规则只负责社区范围、Post Type、原生结构和规避项；匿名、品牌、
  标题、链接和开头规则统一继承全局 Guidance。
- 运行时会合并 Workflow Guidance 与 Editorial Guidance，并拒绝键名重叠或合同不一致。
- 筛选、起草、改写和校验明确采用
  `Guidance` → `Subreddit` → `Audience angle` 的编辑优先级。Post Type、社区风格、
  账号指纹或偏好的 vector database/topic 角度都不能放宽 Disclosure、第一人称或
  Buffer 要求；优先级配置缺失、乱序或职责变化时会 fail closed。
- 规则资源分为两个同步层：JSON 是运行时和 AI 合同，5 个层级/索引审核页加上
  4 个槽位 Markdown 审核页供人工检查；审核页缺失或过期时校验失败。
- Codex 全局与仓库级约定现在都要求变更日志持续使用简体中文，新窗口会从全局
  `~/.codex/AGENTS.md` 继承这一规则。

### 新增

- 新增 Workflow Guidance、Editorial Guidance、4 个槽位、账号引用、截图和 PDF 的
  分层索引与回归覆盖。

## 2026-08-10 — 监测窗口与加权评论情绪

### 新增

- 新增 `Comment Sentiment` 监测结果，使用逐条评论的正/中/负立场、页面可见净分和可见 `Top 1% Commenter` 标识计算 `Positive`、`Mixed`、`Neutral`、`Negative` 或 `None`，不再按积极评论数量简单判断。
- 写入绑定快照保留不含原文和身份的评论权重输入及确定性分数，便于在正式写回前复核总体倾向。

### 变更

- 已发布帖子监测固定为最近 14 天，先按发布日期从新到旧处理 7 天内帖子，再处理第 8–14 天帖子；超过 14 天、缺少发布日期或发布日期在未来的记录只报告跳过，不打开 Reddit 页面。
- 高可见净分的积极评论会增强积极权重；可见负净分较高的消极评论会按社区拒绝方向抵消其负向贡献；Top 1% 评论者的立场使用独立加权，避免任一信号吞掉其他信号。
- 评论净分被四舍五入或隐藏时，监测必须标记为 `Partial` 并说明限制；页面净分只作为可见的社区反馈信号，不被误报为精确 upvote 或 downvote 数。

### 修复

- 监测预览快照现在绑定 `Publish Date`、7/14 天窗口和优先级，预览后目标跨窗或发布日期变化会拒绝旧快照写回。

## 2026-08-07 — 基于浏览器的已发布帖子监测

### 新增

- 新增 `$reddit-browser-monitor`，通过用户选定的 Chrome/Browser 只读检查已发布 Reddit 帖子，输出可见 upvotes、comment count、评论摘要、疑问信号、消极信号、争论信号、Milvus 产品信号和其他数据库竞品信号。
- 新增浏览器观察校验和 write-bound preview snapshot；正式写回前会复核飞书目标行、Publish URL 和字段计划，任一发生变化都会拒绝执行。

### 变更

- 发布后工作流改为浏览器可见页面监测，飞书结果字段改为评论摘要、疑问/消极/争论/产品信号、覆盖状态和监测备注；不再自动修改发布 `Status`。
- 隐藏或四舍五入的指标、未完整审阅的评论必须标记为 `Partial`，不再推断公开页面没有给出的数字。
- 五个评论 Signal 字段统一简化为 `Yes` / `None`，程度、分歧形态和回应紧迫性改由摘要和备注承载。
- 只保留 `Impression (7 days)` 作为独立后台数据字段，浏览器监测不写入、不清空、不估算该值。

### 移除

- 退役人工粘贴 `Reddit JSON Content` 的解析 Skill 和 runtime；内部结构化观察只保存聚合结果，不保存原始评论、用户名或评论链接。

### 修复

- 禁用品牌词门禁现在只限定 Reddit 草稿生成；评论摘要和监测备注会保留评论中真实出现的产品与竞品名，避免产品信号被误删。
- 飞书中已有的 Reddit `/s/` share URL 现在可通过正常浏览器跳转解析为同一 subreddit 的 canonical post URL，不再被误判为不可监测。

### 安全

- 监测禁止 `.json` URL、Reddit API、网络响应、cookies、local storage 和 session 文件，也禁止投票、回复、发帖、私信、关注、举报或任何账号状态变更。

## 2026-08-07 — 指纹权威与语言融合

### 变更

- 硬性通过/失败政策现在只有一个机器可读权威；账号指纹专注于不同的声音实现：
  R1 使用务实的工作判断和实施经验，R2 强调生产环境质疑、工作负载边界和决策标准。
- 第一人称开头、language Buffer 和必需的技术类别示例增加账号级落位指导，减少
  重复的标题/开头模板和孤立的产品名称句子。
- 第一句必须建立第一人称视角，每篇正文至少包含一个与判断或不确定性相关且语法
  正确的 language Buffer。缺少任一项都会阻断校验；Buffer 不能模糊来源事实、
  benchmark 设置或测量值。

### 修复

- 校验现在会拒绝把另一个账号的已知指纹分配给当前账号，不再接受任意已识别的
  fingerprint ID。
- 禁止品牌检查扩展到 `angle` 等生成的审核元数据，不再只检查标题、正文、
  Disclosure 和 mention basis。
- 开头和 language Buffer 检查改为 fail closed，不再只给建议性警告；第一人称只在
  第二句以后出现时同样会失败。

## 2026-08-07 — 第一人称或疑问标题与间接 Milvus 语境

### 变更

- Reddit 标题现在必须使用第一人称单数视角，例如 `I think`、`Now I believe` 或 `What I learned`，或者写成以 `?` 结尾的明确疑问句；完全第三人称的陈述标题会阻断验证。
- 每篇正文仍必须恰好出现一次有来源依据的 Milvus，但必须放在同类技术举例或并列语境中，例如 `vector databases like Milvus`、`data infrastructures such as Milvus` 或 `Milvus and other databases`；直接产品植入会阻断验证。

### 新增

- 增加标题视角、自然 Milvus 上下文、直接植入拒绝和合法同类并列写法的回归测试。

## 2026-08-06 — 正文必须提及 Milvus

### 变更

- 每篇 Reddit 草稿正文现在必须恰好出现一次有来源依据的 Milvus，并填写 `milvus_mention_basis`；正文零次或超过一次都会阻断验证和飞书写入。
- 标题继续完全禁止 Milvus，所有生成内容继续禁止 Zilliz；无法支持一次 Milvus mention 的来源必须被替换，不能补写无依据的品牌内容。
- 随仓库提供的四槽 validation sample 已同步新合同，README 中的标准校验命令可直接通过；当前 live Base 缺少专用 basis 字段时，依据继续保存在 pack JSON 中。

### 新增

- 增加正文零次和两次 Milvus 都失败、正文恰好一次通过的回归测试。

## 2026-08-06 — 第一人称开头与 Post Type 结尾

### 变更

- Reddit 草稿现在在首段立即建立匿名第一人称视角，不再到后续段落才出现账号声音；第一人称仍必须有来源支持，不能补写个人经历。
- 判断和不确定性会加入少量自然 language buffers，例如 `probably`、`one concern I have`、`my current view` 或 `I would likely`；来源支持的事实和指标仍保持直接表达。
- `Tutorial` 以结论、验证步骤或下一步收尾，不再追加社区问题；`Discussion` 如需邀请互动，改用 `Would love to hear your thoughts.` 一类柔和表达，避免生硬的问句结尾。

### 新增

- Draft validation 会拒绝以问题结尾的 `Tutorial`，并提示缺少首段第一人称、缺少自然 language buffer，或以强问句结尾的 `Discussion`。

## 2026-08-04 — 周内容包优先使用近期来源

### 变更

- Weekly Reddit 选题现在优先使用最近 7 天内发布、技术适配且尚未生成的官方 Blog；如果近期来源不能覆盖四个固定槽位，才按发布日期从新到旧使用更早来源补齐。
- Pool sync 与 screening 输出会按来源发布日期排序并标记近期优先候选，使 `--limit` 和人工选题都先处理最新内容。

### 修复

- Feishu Review 写入现在会在创建文档前把来源发布日期转换为 Date 字段要求的毫秒时间戳，避免文档创建后因日期格式错误导致 Base 记录失败。
- 失败恢复可以复用已经创建的 Content Doc，避免重试 weekly delivery 时产生重复文档。

### 新增

- 新增最近 7 天优先规则和回归测试，防止 weekly workflow 重新退化为无日期顺序的候选选择。

## 2026-08-03 — 离线 Reddit JSON Content 解析

### 新增

- 新增 `$reddit-json-content-parse`：只读取人工粘贴到飞书 `Reddit JSON Content` 的完整 JSON，预览并回写互动指标、帖子状态、评论摘要、舆情预警和 Milvus 信号。
- 解析预览会绑定记录集合、字段计划和每条 JSON 内容的 SHA-256；正式写入前若内容或表结构变化会拒绝执行。

### 变更

- 发布后流程改为完全离线解析。空 JSON 内容行显示为等待粘贴，不作为失败，也不会访问 Reddit 或覆盖 `Reddit JSON` / `Reddit JSON Content`。
- 任意检测到的负面评论至少触发 `Watch`；重复或更强的负面讨论可升级为 `Alert`。

### 移除

- 退役会访问 Reddit `.json` 端点的 `$reddit-post-monitor` 及 URL 生成流程，当前仓库只保留人工复制 JSON 后的解析 Skill。

## 2026-08-03 — 已发布 Reddit 帖子监测

### 新增

- 新增 `$reddit-post-monitor`，可通过已发布帖子的公开 `.json` 端点预览 upvotes、评论数、估算 downvotes、upvote ratio 和帖子状态，并在明确授权后写回 Reddit Persona Pipeline。
- 新增评论摘要、`Public Opinion Alert` 和多值 `Milvus Signal`，支持识别负面讨论、Milvus 问题/对比/采用意向及 Zilliz mention，同时不把 Reddit 用户名写入飞书。
- 新增本地 URL JSON 输入、浏览器保存 JSON fallback 和人工分析覆盖文件，允许在 Reddit 对命令行客户端返回 403/429 时继续只读处理，并在 live write 前复核自动评论归纳与信号判断。
- 新增带 digest 的 preview snapshot；live write 只能消费已复核快照，若飞书目标行或字段计划发生变化就拒绝写入。

### 变更

- 发布后状态现在区分 Active、Removed、Deleted、Locked、Archived 和 Unavailable；只有成功确认 Removed/Deleted 时才把原有 `Status` 更新为 `Cancel`。
- Downvote 字段明确标为 `Downvotes (Estimated)`，避免把 Reddit 未公开的精确 downvote 数量误报为真实指标。
- Reddit share link 会先解析到 canonical submission URL；非 HTTPS、非帖子路径和本地输入触发的 live write 会被拒绝，删除作者账号也不再被误判为帖子删除。
- 自动摘要只输出聚合主题和情绪计数，不把原始评论片段写入飞书；评论样本默认关闭，只能显式开启用于本地复核。

## 2026-08-02 — 知识收尾保护措施

### 修复

- 本地生成的 weekly pack 和 PDF 校验临时文件现在默认不进入 Git，降低审核草稿或中间产物被误推到 GitHub 的风险。
- Reference PDF 交付物与当前 Markdown 规则重新同步，LocalLLaMA 周槽位相关说明不再只停留在可编辑源文件中。
- 回归测试现在会检查每个固定周槽位引用的 Markdown 和截图真实存在，避免规则路径与交付资产再次脱节。

## 2026-07-29 — R2 LocalLLaMA 周槽位

### 变更

- R2 的第二个固定周槽位从 `r/dataengineering` 迁移到 `r/LocalLLaMA`，四槽校验、筛选和飞书审核现在统一使用新渠道。
- LocalLLaMA 槽位按新截图支持 `Discussion`、`Question | Help` 和 `Resources`，同时保留 R2 的匿名、无链接、稳定 persona 和来源依据边界。
- R2 的 topic 匹配扩展到本地模型、自托管推理、量化、硬件适配和本地 RAG，不再推荐退役的 data engineering 槽位。

## 2026-07-24 — 初始精简版 Reddit 流程

### 新增

- 建立 `$reddit-weekly` 路由 Skill 和五个可独立调用的阶段 Skills，支持完整 weekly workflow 或只运行指定阶段。
- 增加 `short_post`，同时保留 `standard_post`、`long_post` 和 `code_long_post`。
- 增加 Published-only sync、开放问题可选、匿名、品牌、无链接和长度档位回归测试。
- 补充项目 README、目录职责、逐步输入输出、JSON 判断规则、冲突决议和 Change Log 维护规范。

### 变更

- Pool sync 固定从 Content All in One / `All content` / `all content` 读取，只接收 `Category = Blog Post` 且 `Status = Published` 的官方 Blog。
- Weekly 内容压缩为 R1/R2 四个固定槽位；两个账号都匿名、空 Disclosure、始终 `no_link`。
- 标题禁止 Milvus；正文允许一次有依据的 Milvus mention；生成内容完全禁止 Zilliz。
- 开放问题从强制结尾改为完全可选，缺少问题不会产生 error 或 warning。
- 项目 runtime 提升到根目录，Skills 统一收进 `.agents/skills/`，不再把 Reddit runtime 包装成独立 Agent 目录。

### 移除

- 移除旧 5–6 账号、warm-up、Medium/calendar sync、local CSV pool/write、subreddit research runtime 和历史 pack 残留。
- 移除已被 README、AGENTS 和机器规则取代的 handoff、账号说明、结构审计和冲突审计副本。
## 2026-08-24 — James Luan 来源专用策略

### 新增

- Pool sync 会完整纳入 James Luan 撰写的已发布官方 Blog，即使文章早于普通来源截止日期；官方 URL、发布日期和去重等安全检查仍然生效，并保留来源作者供后续阶段识别。
- James Luan 来源现在为 R1 和 R2 使用固定身份披露。R1 将核心观点改写为戏剧化、带克制幽默感的中等篇幅帖子；R2 附上原文链接，并邀请读者在评论区分享观点或产品体验。

### 变更

- 匿名和无链接规则改为来源条件化合同：非 James 来源继续保持 R1/R2 匿名、空 Disclosure 和 `no_link`，只有 James 来源启用指定披露及 R2 原文链接例外。
- 改写路由现在明确以来源作者区分：James 来源使用各账号的专用策略，非 James 来源继续使用原有账号人设、按内容需要选择篇幅，不再把短帖作为 James 策略特征。
- 草稿校验和飞书内容渲染会确认披露、短帖档位、来源链接及互动邀请真实进入最终 post，避免规则只停留在说明或审核元数据中。
