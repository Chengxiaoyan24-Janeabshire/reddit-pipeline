---
name: reddit-weekly
description: >
  Run the complete fixed R1/R2 weekly Reddit content workflow across All Content
  pool sync, source screening, four-slot drafting, validation, and Feishu review
  delivery. Use for "跑本周的post", "生成 reddit 周内容包", or an explicit
  end-to-end weekly run. This skill creates review drafts only and never performs
  Reddit login, posting, replies, comments, voting, or account activity.
---

# Reddit Weekly

Run the five independent stage Skills in order. Run shared commands from the
project root.

## Independent Skills

- `../reddit-pool-sync/SKILL.md`
- `../reddit-source-screen/SKILL.md`
- `../reddit-pack-draft/SKILL.md`
- `../reddit-pack-validate/SKILL.md`
- `../reddit-pack-write/SKILL.md`

Read each selected skill completely before executing its stage. A user may call
any one of these skills directly without triggering later stages.

## Weekly Workflow

1. Use `$reddit-pool-sync` to sync eligible `Category = Blog Post` and
   `Status = Published` rows from Content All in One / `all content`
   (`vewx5CDVdU`).
2. Use `$reddit-source-screen` to screen active ungenerated rows.
3. Use `$reddit-pack-draft` to produce exactly four slots:
   - R1 → `r/Rag`
   - R1 → `r/AI_Agents`
   - R2 → `r/vectordatabase`
   - R2 → `r/LocalLLaMA`
4. Use `$reddit-pack-validate` with weekly enforcement.
5. Use `$reddit-pack-write` to preview, then write to Feishu review only after
   validation succeeds.

Stop before delivery when the user asks only to inspect, screen, draft,
validate, or preview.

## Shared Contract

- Treat `data/weekly_post_rules.json` as the machine-readable source of truth.
- Use only R1/R2 and their fixed subreddit lanes.
- Preserve the stable account fingerprint from `data/user_fingerprints.json`.
  Use subreddit screenshots only as Post Type and structure overlays; never copy
  their usernames, identity, employer, disclosure, links, typos, or claims.
- Keep both accounts anonymous and `disclosure` empty. `I built` is allowed only
  when source-supported and must not reveal identity, employer, contributor or
  maintainer status, or affiliation.
- Do not mention Milvus in a title. A body may mention Milvus once when the
  technical background or data is source-supported; fill
  `milvus_mention_basis`. Never mention Zilliz.
- R1 and R2 are always `no_link`; reject URLs and `approved_link`.
- Do not invent development history, customers, benchmarks, metrics, or results.
- Open community questions are optional. Keep one when it fits naturally and do
  not force a question ending.
- Use `short_post` for genuine concise discussions or Resource Requests and
  keep `standard_post` for normal technical posts.
- Do not generate warm-up activity.
- Never automate Reddit account activity. Human owners review and publish.

## Delivery Report

Report the stages actually run, structured counts, validation warnings, and any
Feishu review rows/docs created. State which stages were intentionally skipped.
