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
2. Use `$reddit-source-screen` to screen active ungenerated rows, prioritizing
   sources from the latest 7 days. Use older suitable rows only when recent
   sources cannot cover all four fixed slots.
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
- Apply `source_recency_policy`: recent suitable sources come first, followed
  by older suitable sources in descending publish-date order only as fallback.
- Use only R1/R2 and their fixed subreddit lanes.
- Preserve the stable account fingerprint from `data/user_fingerprints.json`.
  Use subreddit screenshots only as Post Type and structure overlays; never copy
  their usernames, identity, employer, disclosure, links, typos, or claims.
- Treat the fingerprint as voice realization, not a second hard-rule file: R1
  should sound like a practical working build log, while R2 should sound like a
  production design decision grounded in workload and operational criteria.
- Keep both accounts anonymous and `disclosure` empty. `I built` is allowed only
  when source-supported and must not reveal identity, employer, contributor or
  maintainer status, or affiliation.
- Every title uses first-person singular framing or is an explicit question
  ending in `?`; fully third-person declarative titles are rejected.
- Do not mention Milvus in a title. Every body must mention Milvus exactly once
  using source-supported technical background or data; fill
  `milvus_mention_basis`. Phrase it indirectly as a category example or peer,
  such as `vector databases like Milvus`, `data infrastructures such as Milvus`,
  or `Milvus and other databases`. Reject direct product placement and replace a
  source that cannot support the natural context. Never mention Zilliz.
- R1 and R2 are always `no_link`; reject URLs and `approved_link`.
- Do not invent development history, customers, benchmarks, metrics, or results.
- The first sentence must establish a source-supported first-person perspective.
  Every body must include at least one grammatical language buffer for a
  judgment or uncertainty; never use buffers to hedge source-supported facts or
  measurements. Missing either fails validation.
- Tutorials must not end with a question. Discussion reply invitations are
  optional and should use a soft conversational close rather than a hard
  interrogative ending.
- Use `short_post` for genuine concise discussions or Resource Requests and
  keep `standard_post` for normal technical posts.
- Do not generate warm-up activity.
- Never automate Reddit account activity. Human owners review and publish.

## Delivery Report

Report the stages actually run, structured counts, validation warnings, and any
Feishu review rows/docs created. State which stages were intentionally skipped.
