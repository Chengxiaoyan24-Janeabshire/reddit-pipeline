# Reddit Weekly Pipeline

> 基本规则
>
> - 只生成供人工审核和手动发布的 Reddit 草稿，不登录、不发帖、不回复、不点赞、不投票、不养号。
> - 每周固定四个槽位：R1 → `r/Rag`、`r/AI_Agents`；R2 → `r/vectordatabase`、`r/LocalLLaMA`。
> - R1/R2 绝对匿名，Disclosure 为空；`I built` 可以保留，但必须有来源支持且不能暴露身份或 affiliation。
> - 标题不能出现 Milvus；正文最多出现一次 Milvus，并填写来源依据；任何生成内容不能出现 Zilliz。
> - R1/R2 全部 `no_link`，标题、正文和链接字段都不能有 URL。
> - 开放问题可有可无，不为满足校验强行添加。
> - 保留 `short_post`、`standard_post`、`long_post`、`code_long_post` 四个长度档位。

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
```

`$reddit-weekly` 顺序协调五个阶段；五个阶段 Skill 也可以单独调用，单独调用时不会自动进入后续阶段。

## 2. Skills 与触发方式

| Skill | 功能 | 输出或写入 |
|---|---|---|
| `reddit-weekly` | 跑完整 weekly workflow | 四槽内容包及经授权的 Feishu 审核记录 |
| `reddit-pool-sync` | 只预览或同步符合条件的官方 Blog | `Reddit Blog Pool` 新记录或 dry-run JSON |
| `reddit-source-screen` | 只筛选来源并分配 R1/R2、Subreddit、Post Type | 筛选 JSON；经授权时更新 Blog Pool 字段 |
| `reddit-pack-draft` | 只生成 Reddit-native 草稿 JSON | Pack JSON，不写 Feishu 或 Reddit |
| `reddit-pack-validate` | 只校验草稿 | `{ok, validated, errors, warnings}`，无写入 |
| `reddit-pack-write` | 预览或写入已经校验的草稿 | Feishu Content Docs 和 Persona Pipeline rows |

常用触发：

- “跑本周的 post” → `$reddit-weekly`
- “同步最新的 pool” → `$reddit-pool-sync`
- “筛选 Reddit pool” → `$reddit-source-screen`
- “给这篇 blog 起草 Reddit 内容” → `$reddit-pack-draft`
- “检查这个 Reddit pack” → `$reddit-pack-validate`
- “把已批准的 pack 写进飞书” → `$reddit-pack-write`

## 3. 每一步的输入与输出

| 步骤 | 输入 | 判断规则 | 输出 / 外部写入 |
|---|---|---|---|
| Pool sync | Content All in One `all content` view、cutoff date | `Category = Blog Post`、`Status = Published`、官方 `/blog/` URL、发布日期 ≥ `2026-01-01`、canonical URL 去重 | Dry run 只返回计数和候选；live sync 只新增 `Reddit Blog Pool` rows |
| Source screen | Pending pool row 或单个 URL；抓取到的正文；topic/account rules | 技术密度、campaign/press 风险、R1/R2 topic score、固定 lane、Post Type | 筛选状态、分数、理由、Topic、Account、Subreddit、Post Type、`no_link` |
| Draft | 已筛选来源事实；账号、指纹、长度、weekly、subreddit 与截图规则 | 先应用硬规则，再应用稳定指纹，再叠加 Post Type/截图结构，最后写来源事实 | 只返回最终 Pack JSON，不返回推理或私密账号信息 |
| Validate | 单个 pack 或 pack 列表 | 四槽、账号/社区、Post Type、匿名、Milvus/Zilliz、URL、长度、代码、重复正文 | 只读 JSON；开放问题有无都不报错或警告 |
| Feishu review | 已通过 validation 的 pack | 再校验、构造无链接 Content Doc、映射 review metadata | Dry run 只预览；live write 创建 Docs/rows 并增加 pool 生成计数 |
| Manual publish | 人工批准的草稿 | 人工决定是否发布 | 人工维护 `Status`、`Publish URL`、`Publish Date`、`Publisher` |

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
      "title": "...",
      "body": "...",
      "disclosure": "",
      "link_policy": "no_link",
      "milvus_mention_basis": "",
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
| `data/weekly_post_rules.json` | Screen、Draft、Validate | R1/R2、四个固定槽位、Post Types、匿名、品牌、链接、开放问题策略 | 机器可读硬规则，优先级最高 |
| `data/accounts.json` | Screen、Draft、Validate、Write | 账号角色、允许社区、默认 fingerprint、品牌边界 | 定义稳定 persona，不能扩大 weekly lane |
| `data/account_topic_rules.json` | Screen | topic/keyword score 和 R1/R2 分配倾向 | 只排名，不创建新的 subreddit 权限 |
| `data/user_fingerprints.json` | Draft、Validate | 长期稳定语气、格式和截图可叠加范围 | 胜过截图中的身份、拼写、链接和个人主张 |
| `data/subreddits.json` | Draft guidance、Feishu schema | 社区适配、Post Type 与 native 结构摘要 | 不能覆盖 weekly hard rules |
| `data/content_length_rules.json` | Draft、Validate、Feishu schema | 四种长度/代码范围 | `short_post` 不替代保留的长档位 |
| `data/topic_bank.json` | Screen、Review tags | topic taxonomy 与 advisory community fit | 必须与账号固定 lane 取交集 |
| `config/feishu-fields.json` | Write | 本地字段到 Feishu 字段名映射 | 不是编辑规则 |
| `config/feishu-tables.json` | Sync、Screen、Write | 当前 Base/table/view IDs | 不是编辑规则，不存 credentials |
| `samples/weekly_pack.example.json` | Validation sample | 合法四槽输入示例 | 不是规则来源 |

规则优先级：`AGENTS.md / latest user direction` → `weekly_post_rules.json` → stable account/persona JSON → subreddit Markdown/screenshots → source-specific facts。截图只能影响 Post Type、开头结构、段落密度、bullets 和提问形状。

## 6. 已解决的规则冲突

| 冲突 | 现行结论 |
|---|---|
| 旧资料中的 5–6 个账号、warm-up、回复、点赞或发帖自动化 | 只保留 R1/R2 四槽内容生成；所有 Reddit 操作由人工完成 |
| 稳定“指纹/人设”与 subreddit 截图作者风格不同 | 稳定 fingerprint 是 persona；截图只是 Post Type/结构 overlay，不复制身份、雇主、链接、错别字、metrics 或经历 |
| 旧规则要求完全不提 Milvus，其他例子又偏产品宣传 | 标题不提；正文最多一次且需要 source-supported basis；绝不提 Zilliz |
| 旧 R1 manual-approved link 与示例中的 inline URL | R1/R2 统一 `no_link`，URL 和 `approved_link` 都拒绝 |
| 旧同步链指向 Medium 或 calendar，并接受非 Published | 只从 All Content 的固定 view 同步 `Blog Post + Published` |
| 旧规则强制以开放问题结尾 | 开放问题完全可选，有则保留，没有也不报错或警告 |
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
| `Reddit Persona Pipeline` (`tbl7OQ8PLU0iwJNp`) | Draft metadata、Content Doc、Milvus 依据、长度、审核与人工发布状态 |

主要 review 字段：`Draft ID`、`Source Blog URL`、`Blog Pool Record ID`、`Account Code`、`Subreddit`、`Post Type`、`Content Doc`、`Link Policy`、`Milvus Mention Basis`、`Voice Fingerprint`、`Length Tier`、`Status`、`Publish URL`、`Publish Date` 和 `Publisher`。

## 9. 主要目录

| 路径 | 内容 |
|---|---|
| `.agents/skills/` | 一个 weekly router 和五个可独立调用的阶段 Skills；不是独立 runtime 或 Agent 项目 |
| `scripts/` | 当前有效的 sync、screen、validate、Feishu write、schema setup 和 PDF rebuild runtime |
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

# Regression tests
python3 -m unittest tests.test_rules
```

## 11. Change Log 怎么维护

每次准备 push 行为、规则或用户流程变化时，同一批 commit 必须更新 [`CHANGELOG.md`](CHANGELOG.md)。标题使用 `YYYY-MM-DD — 简短主题`，按需使用 `Added`、`Changed`、`Fixed`、`Removed`、`Security`。每条说明用户或 runtime 得到了什么变化，不写成文件名列表。
