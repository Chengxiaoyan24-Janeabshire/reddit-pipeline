---
name: reddit-weekly
description: >
  Run the complete currently configured Reddit weekly workflow across source
  sync, screening, drafting, validation, and Feishu review delivery. Use for
  "跑本周的post", "生成 reddit 周内容包", or an explicit end-to-end weekly run.
  This Skill creates review drafts only and never performs Reddit account
  activity.
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

Read each selected Skill completely before executing its stage. A user may call
one stage directly without triggering later stages.

## Workflow

1. Load the current weekly and sync contracts from `guidance/reddit/workflow/`.
2. Use `$reddit-pool-sync` to preview or perform the authorized source sync.
3. Use `$reddit-source-screen` to screen sources in configured recency order.
4. Use `$reddit-pack-draft` to create the current configured slots.
5. Use `$reddit-pack-validate` with weekly enforcement.
6. Use `$reddit-pack-write` to preview, then write only after authorization.

Stop before delivery when the user asks only to inspect, screen, draft,
validate, or preview.

## Shared Contract

- `guidance/reddit/workflow/` owns current execution values such as quantity,
  accounts, slots, recency, sync, and the R2 short-question quota; these values
  are outside editorial precedence.
- For editorial decisions, apply `Guidance` first, the selected `Subreddit`
  second, and the `Audience angle` third. Higher levels always win.
- `guidance/` owns Disclosure, first-person `I`, language Buffer, and the other
  global editorial and safety rules.
- `reference/slots/` owns community subrules, valid Category/Post Type, native
  structure, and style within Guidance.
- `reference/accounts/` and `reference/topic_bank.json` own audience-preferred
  angles, topic fit, and fingerprints within both higher layers.
- `resource/` supplies optional visual evidence only.
- Machine JSON is the runtime authority. Generated `RULES.md`,
  `TOPIC_RULES.md`, and slot Markdown files are human review views only.
- Source facts bound every claim.
- Reject or replace a source when no lower-level choice can satisfy the higher
  levels; never relax Guidance or Subreddit rules to preserve an audience angle.
- Never invent experience, customers, benchmarks, metrics, or results.
- Never automate Reddit login, publishing, comments, replies, voting, likes,
  warm-up, or coordinated engagement.
- After any rule change, run `python3 scripts/render_rule_docs.py` and require
  `python3 scripts/render_rule_docs.py --check` to pass.

## Delivery Report

Report the stages actually run, structured counts, validation warnings, and any
Feishu review rows or Docs created. State which stages were skipped.
