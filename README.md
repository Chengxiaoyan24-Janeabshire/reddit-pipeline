# Reddit Weekly Pipeline

> 基本规则
>
> - 只生成供人工审核和手动发布的 Reddit 草稿，不登录、不发帖、不回复、不点赞、不投票、不养号。
> - 每周固定四个槽位：R1 → `r/Rag`、`r/AI_Agents`；R2 → `r/vectordatabase`、`r/LocalLLaMA`。
> - R1/R2 绝对匿名，Disclosure 为空；`I built` 可以保留，但必须有来源支持且不能暴露身份或 affiliation。
> - 标题必须使用第一人称单数视角，或写成以 `?` 结尾的明确疑问句；不能使用完全第三人称的陈述标题，且标题不能出现 Milvus。
> - 每篇正文必须恰好出现一次有来源依据的 Milvus，并填写 `milvus_mention_basis`；提及必须放在同类技术举例或并列语境中，例如 `vector databases like Milvus`，不能直接植入；任何生成内容不能出现 Zilliz。
> - R1/R2 全部 `no_link`，标题、正文和链接字段都不能有 URL。
> - 第一句必须建立有来源支持的第一人称视角；每篇正文至少使用一个自然、合乎语法的 language buffer，且只能修饰判断或不确定性。缺少任一项都会阻断验证。Tutorial 不以问题结尾，Discussion 如邀请互动则使用柔和表达。
> - 保留 `short_post`、`standard_post`、`long_post`、`code_long_post` 四个长度档位。
> - 本周选题优先使用最近 7 天发布、技术适配且尚未生成的 Blog；不足四槽时才按发布日期从新到旧使用更早来源。
> - 已发布帖子只解析人工粘贴到飞书的完整 Reddit JSON；不会由脚本访问 Reddit。Reddit 不公开精确 downvote，表中只保存明确标注的估算值。

## 1. 整个 Pipeline 的逻辑

```text
Content All in One / All content / all content
  └─ Category = Blog Post + Status = Published + official /blog/ URL
      └─ reddit-pool-sync
          └─ Reddit Blog Pool
              └─ reddit-source-screen
                  ├─ 技术适配与风险筛选
                  ├─ R1/R2 分配
                  └─ 固定 Subreddit + Post Type 推荐
                      └─ reddit-pack-draft
                          └─ 四槽或单来源 Draft JSON
                              └─ reddit-pack-validate
                                  ├─ 账号/槽位/Post Type
                                  ├─ 匿名/品牌/链接
                                  ├─ 指纹/长度/重复内容
                                  └─ 只读校验
                                      └─ reddit-pack-write
                                          ├─ Dry run 预览
                                          └─ Feishu Content Doc + Review rows

人工审核与发布
  └─ 在 Reddit Persona Pipeline 维护发布状态
      └─ reddit-json-content-parse
          ├─ 读取 Reddit JSON Content
          ├─ 更新 votes/comments 与帖子状态
          ├─ 汇总评论和负面舆情预警
          └─ 标记评论中的 Milvus 信号
```

`$reddit-weekly` 顺序协调五个阶段；五个阶段 Skill 也可以单独调用，单独调用时不会自动进入后续阶段。
`$reddit-json-content-parse` 是发布后的独立离线解析/飞书写回流程，不属于 weekly drafting 阶段。

## 2. Skills 与触发方式

| Skill | 功能 | 输出或写入 |
|---|---|---|
| `reddit-weekly` | 跑完整 weekly workflow | 四槽内容包及经授权的 Feishu 审核记录 |
| `reddit-pool-sync` | 只预览或同步符合条件的官方 Blog | `Reddit Blog Pool` 新记录或 dry-run JSON |
| `reddit-source-screen` | 只筛选来源并分配 R1/R2、Subreddit、Post Type | 筛选 JSON；经授权时更新 Blog Pool 字段 |
| `reddit-pack-draft` | 只生成 Reddit-native 草稿 JSON | Pack JSON，不写 Feishu 或 Reddit |
| `reddit-pack-validate` | 只校验草稿 | `{ok, validated, errors, warnings}`，无写入 |
| `reddit-pack-write` | 预览或写入已经校验的草稿 | Feishu Content Docs 和 Persona Pipeline rows |
| `reddit-json-content-parse` | 解析人工粘贴的 Reddit JSON | Dry-run JSON + 绑定快照；经授权时更新互动、状态、评论摘要与信号字段 |

常用触发：

- “跑本周的 post” → `$reddit-weekly`
- “同步最新的 pool” → `$reddit-pool-sync`
- “筛选 Reddit pool” → `$reddit-source-screen`
- “给这篇 blog 起草 Reddit 内容” → `$reddit-pack-draft`
- “检查这个 Reddit pack” → `$reddit-pack-validate`
- “把已批准的 pack 写进飞书” → `$reddit-pack-write`
- “解析 Reddit JSON Content 并更新互动和评论” → `$reddit-json-content-parse`

## 3. 每一步的输入与输出

| 步骤 | 输入 | 判断规则 | 输出 / 外部写入 |
|---|---|---|---|
| Pool sync | Content All in One `all content` view、cutoff date | `Category = Blog Post`、`Status = Published`、官方 `/blog/` URL、发布日期 ≥ `2026-01-01`、canonical URL 去重；发布日期倒序并标记最近 7 天 | Dry run 只返回计数和候选；live sync 只新增 `Reddit Blog Pool` rows |
| Source screen | Pending pool row 或单个 URL；抓取到的正文；topic/account rules | 最近 7 天优先、技术密度、campaign/press 风险、R1/R2 topic score、固定 lane、Post Type | 筛选状态、分数、理由、Topic、Account、Subreddit、Post Type、`no_link` |
| Draft | 已筛选来源事实；账号、指纹、长度、weekly、subreddit 与截图规则 | 先应用硬规则，再应用稳定指纹，再叠加 Post Type/截图结构，最后写来源事实 | 只返回最终 Pack JSON，不返回推理或私密账号信息 |
| Validate | 单个 pack 或 pack 列表 | 四槽、账号/社区、Post Type、标题视角、匿名、Milvus 自然提及、禁用品牌词、URL、长度、代码、重复正文 | 只读 JSON；硬规则失败会阻断写入 |
| Feishu review | 已通过 validation 的 pack | 再校验、构造无链接 Content Doc、映射 review metadata | Dry run 只预览；live write 创建 Docs/rows 并增加 pool 生成计数 |
| Manual publish | 人工批准的草稿 | 人工决定是否发布 | 人工维护 `Status`、`Publish URL`、`Publish Date`、`Publisher` |
| JSON content parse | `Status = Published` 的 review row 及人工粘贴的 `Reddit JSON Content` | 离线校验 JSON、解析帖子状态、评论内容、舆情和 Milvus 信号；不请求 Reddit，不读取 Reddit author 字段 | 空内容行列为等待；默认只预览并生成绑定快照；经授权时只按该快照更新 Feishu |

同步源固定为：

- Base：`TXy3bCKznaz89fseyo3cPMShnyb`
- Table：`All content`（`tblsyUaNiyPnhrFI`）
- View：`all content`（`vewx5CDVdU`）
- Category：`Blog Post`
- Status：`Published`

飞书里的真实选项是 `Blog Post`；口述的 “Post Blog” 只映射到这个现有选项。`Posted`、`Planned` 和其他状态都不会同步。Medium Sync、Medium Daily、EN Content 和旧 calendar view 都不是来源。

## 4. Draft JSON 合同

```json
{
  "source_title": "...",
  "source_url": "https://official-source.example/blog/...",
  "pool_record_id": "rec...",
  "items": [
    {
      "account_code": "R1",
      "content_type": "technical_post",
      "subreddit": "r/Rag",
      "post_type": "Discussion",
      "title": "What I learned about ...",
      "body": "...",
      "disclosure": "",
      "link_policy": "no_link",
      "milvus_mention_basis": "The source-supported reason for the single body mention.",
      "angle": "...",
      "voice_fingerprint": "personal_build_log",
      "length_tier": "standard_post"
    }
  ]
}
```

`source_url` 是内部审核 metadata，可以保存官方来源 URL；生成的 `title`、`body` 和 `approved_link` 不能包含链接。

## 5. JSON 文件怎样判断

| JSON | 使用阶段 | 决定什么 | 权限边界 |
|---|---|---|---|
| `data/weekly_post_rules.json` | Screen、Draft、Validate | R1/R2、四个固定槽位、最近 7 天来源优先、Post Types、标题视角、匿名、品牌自然提及、链接和收尾策略 | 机器可读硬规则，优先级最高 |
| `data/accounts.json` | Screen、Draft、Validate、Write | 账号角色、默认 fingerprint 和简短 persona 摘要 | 不复制 hard rules，也不能扩大 weekly lane |
| `data/account_topic_rules.json` | Screen | topic/keyword score 和 R1/R2 分配倾向 | 只排名，不创建新的 subreddit 权限 |
| `data/user_fingerprints.json` | Draft、Validate | 长期稳定语气、标题/首段/缓冲语的账号化实现和截图可叠加范围 | 只决定“怎样说”，不重复或覆盖 hard rules |
| `data/subreddits.json` | Draft guidance、Feishu schema | 社区 fit 与 native 结构摘要；Post Type 不在这里重复 | 不能覆盖 weekly hard rules |
| `data/content_length_rules.json` | Draft、Validate、Feishu schema | 四种长度/代码范围 | `short_post` 不替代保留的长档位 |
| `data/topic_bank.json` | Screen、Review tags | topic taxonomy 与 advisory community fit | 必须与账号固定 lane 取交集 |
| `config/feishu-fields.json` | Write | 本地字段到 Feishu 字段名映射 | 不是编辑规则 |
| `config/feishu-tables.json` | Sync、Screen、Write | 当前 Base/table/view IDs | 不是编辑规则，不存 credentials |
| `samples/weekly_pack.example.json` | Validation sample | 合法四槽输入示例 | 不是规则来源 |

规则优先级：`AGENTS.md / latest user direction` → `weekly_post_rules.json` → stable account/persona JSON → subreddit Markdown/screenshots。来源事实不是可被低优先级覆盖的风格层；所有经历、数据、结果和技术主张都必须受来源约束。截图只能影响 Post Type、开头结构、段落密度、bullets 和提问形状。

### 5.1 语言要求怎样融入 fingerprint

硬规则只判断草稿能否通过；fingerprint 决定通过后的内容分别像 R1 还是 R2；subreddit overlay 决定 Post Type 和结构；来源决定能说哪些事实。

| 语言维度 | R1 `personal_build_log` | R2 `structured_design_question` |
|---|---|---|
| 标题 | 用当前实践判断或经验归纳，例如 `I'm starting to think...`、`What I learned...`、`I keep coming back to...` | 用生产怀疑或决策门槛，例如 `I'm not convinced...`、`I would only...`、`What would make me...` |
| 第一句 | 从“我现在怎样看、担心或处理这个问题”进入具体实现，不把来源摘要伪装成个人经历 | 先说当前系统判断，再马上给 workload、成本、可靠性或运维约束 |
| Language buffer | `one concern I have`、`my current view`、`I would probably`、`I tend to` | `I suspect`、`I'm not convinced`、`I would likely`、`it probably depends on` |
| 必需技术举例 | 把 `vector databases like Milvus` 一类语境放进 checklist、retrieval decision 或可观察的系统边界 | 把同类举例放进 execution path、benchmark method、migration 或 operations comparison |
| Discussion 收尾 | 延续 build-log 语气，柔和邀请补充案例或遗漏条件 | 先写清未解决的判断标准，再决定是否加低压力邀请 |

每篇正文至少需要一个合乎语法的 Language buffer；第一句缺少第一人称或全文缺少 buffer 都是 error。Buffer 只修饰判断、建议和不确定性，不修饰来源已经支持的测试设置、测量值或事实。Milvus 句子也不是固定模板：它必须承担所在段落的技术功能，不能单独加一句只为满足计数。

## 6. 已解决的规则冲突

| 冲突 | 现行结论 |
|---|---|
| 旧资料中的 5–6 个账号、warm-up、回复、点赞或发帖自动化 | 只保留 R1/R2 四槽内容生成；所有 Reddit 操作由人工完成 |
| 稳定“指纹/人设”与 subreddit 截图作者风格不同 | 稳定 fingerprint 是 persona；截图只是 Post Type/结构 overlay，不复制身份、雇主、链接、错别字、metrics 或经历 |
| 旧规则要求完全不提 Milvus，其他例子又偏产品宣传 | 标题不提；每篇正文恰好一次且需要 source-supported basis，并以同类数据库/数据基础设施举例或并列的方式自然出现，禁止直接植入；绝不提 Zilliz |
| 旧标题使用完全第三人称陈述 | 每个标题必须使用第一人称单数视角，或写成以 `?` 结尾的明确疑问句 |
| 旧 R1 manual-approved link 与示例中的 inline URL | R1/R2 统一 `no_link`，URL 和 `approved_link` 都拒绝 |
| 旧同步链指向 Medium 或 calendar，并接受非 Published | 只从 All Content 的固定 view 同步 `Blog Post + Published` |
| 旧规则强制以开放问题结尾 | Tutorial 不以问题结尾；Discussion 的互动邀请可选，使用柔和表达而非生硬问句 |
| `topic_bank.json` 的广泛 community fit 与账号固定 lane | Topic 只能帮助排序，最终必须服从四个固定槽位 |
| Tools/Blog/Open Source/Showcase 经常依赖外链 | 只有内容在无链接时仍完整，才使用该 Post Type；否则换角度或换来源 |

## 7. 四种长度档位

| Tier | 目标 | 适用内容 |
|---|---|---|
| `short_post` | 60–160 words；允许 40–220 | 简短 Discussion、Resource Request、单一聚焦问题 |
| `standard_post` | 180–380 words；允许 140–480 | 默认技术讨论和比较 |
| `long_post` | 340–850 words；允许 320–1100 | 深度比较、postmortem、生产复盘、benchmark 方法 |
| `code_long_post` | 340–950 words；允许 320–1200 | 最多 2 个短代码块、总计最多 45 行的实现或调试内容 |

长度不足或超出允许范围会产生 review warning；代码放进非 code tier 会产生 error。不要为达到长档位而填充内容。

## 8. Feishu 表与字段

| 表 | 用途 |
|---|---|
| `Reddit Blog Pool` (`tbl3yFyNWxEdC9OT`) | 来源、发布日期、筛选、Topic、R1/R2 和 Post Type 推荐 |
| `Reddit Persona Pipeline` (`tbl7OQ8PLU0iwJNp`) | Draft metadata、Content Doc、长度、审核与人工发布状态；可用字段存在时也写入 Milvus 依据 |

主要 review 字段：`Draft ID`、`Source Blog URL`、`Blog Pool Record ID`、`Account Code`、`Subreddit`、`Post Type`、`Content Doc`、`Link Policy`、`Voice Fingerprint`、`Length Tier`、`Status`、`Publish URL`、`Publish Date` 和 `Publisher`。`Milvus Mention Basis` 已在本地 schema 映射中定义，但当前 live Base 尚无该专用字段；writer 会跳过不存在的字段，依据仍以 pack JSON 中非空的 `milvus_mention_basis` 为准。

发布后人工输入字段：`Reddit JSON`（可选链接）和 `Reddit JSON Content`（完整 JSON 文本）。解析结果字段：`Upvotes`、`Comments`、`Downvotes (Estimated)`、`Upvote Ratio`、`Reddit Post Status`、`Comment Summary`、`Public Opinion Alert`、`Milvus Signal` 和 `Reddit Metrics Updated At`。解析 Skill 不会覆盖两个输入字段；只有有效 JSON 证明 `Removed`/`Deleted` 时才自动把现有 `Status` 改为 `Cancel`。

## 9. 主要目录

| 路径 | 内容 |
|---|---|
| `.agents/skills/` | 一个 weekly router、五个 drafting 阶段 Skills 和一个发布后 JSON 解析 Skill；不是独立 runtime 或 Agent 项目 |
| `scripts/` | 当前有效的 sync、screen、validate、Feishu write、JSON content parse、schema setup 和 PDF rebuild runtime |
| `data/` | 账号、topic、fingerprint、weekly、subreddit 与长度机器规则 |
| `config/` | 无 secret 的 Feishu table/view ID、字段映射和 credential template |
| `reference/` | 可编辑 Markdown、生成的 PDF，以及 subreddit Post Type/结构截图 |
| `samples/` | 可复用的四槽 validation sample，不是规则来源 |
| `tests/` | Published-only、开放问题、长度、匿名、品牌和 no-link 回归测试 |
| `AGENTS.md` | Agent 必须遵守的最小运行与安全合同 |
| `CHANGELOG.md` | 每次 GitHub push 的行为、规则和用户结果摘要 |

项目不提交虚拟环境、浏览器日志、历史 pack、本地 CSV pool、generated output 或 Feishu credentials。

## 10. 本地运行与验证

安装：

```bash
bash setup.sh
```

凭据使用 `config/feishu-config.template.json` 的结构，实际文件放在 `config/feishu-config.json`（已 gitignore）或通过 `FEISHU_CONFIG_PATH` 指向仓库外文件。

常用命令：

```bash
# Pool sync preview
python3 scripts/sync_blog_pool_from_content_all_in_one.py --since-date 2026-01-01 --dry-run

# Feishu source screening preview
python3 scripts/screen_feishu_pool.py --dry-run

# One-URL screening without writes
python3 scripts/screen_and_assign.py --url "https://milvus.io/blog/example" --title "Example" --no-fetch

# Four-slot validation
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < samples/weekly_pack.example.json

# Feishu delivery preview
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < samples/weekly_pack.example.json

# Parse pasted Reddit JSON Content and create a write-bound snapshot;
# no Feishu fields or records are changed
python3 scripts/parse_reddit_json_content.py \
  --from-feishu \
  --sample-comments 12 \
  --snapshot-out packs/reddit-json-content-preview.json

# Optional: replace automatic summary/alert/signal values with reviewed values
python3 scripts/parse_reddit_json_content.py \
  --from-feishu \
  --analysis-json packs/reddit-json-analysis.json \
  --snapshot-out packs/reddit-json-content-preview.json

# Live Feishu update after explicit approval of the exact preview snapshot
python3 scripts/parse_reddit_json_content.py \
  --from-feishu \
  --ensure-fields \
  --snapshot-in packs/reddit-json-content-preview.json \
  --write

# Regression tests
python3 -m unittest
```

## 11. Change Log 怎么维护

每次准备 push 行为、规则或用户流程变化时，同一批 commit 必须更新 [`CHANGELOG.md`](CHANGELOG.md)。标题使用 `YYYY-MM-DD — 简短主题`，按需使用 `Added`、`Changed`、`Fixed`、`Removed`、`Security`。每条说明用户或 runtime 得到了什么变化，不写成文件名列表。
