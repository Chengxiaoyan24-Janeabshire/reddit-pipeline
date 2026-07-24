---
name: reddit-source-screen
description: >
  Screen pending Reddit Blog Pool rows or one supplied blog URL for technical
  suitability, R1/R2 assignment, fixed subreddits, Post Types, and topic fit.
  Use for "$reddit-source-screen", "筛选 Reddit pool", or checking whether one
  source fits the Reddit lanes. Do not draft or deliver content.
---

# Reddit Source Screen

Run commands from the project root.

## Required Rules

Read `data/account_topic_rules.json`, `data/topic_bank.json`, and
`data/weekly_post_rules.json`. Assign only active R1/R2 lanes and at most two
accounts. Every recommendation uses `link_policy = no_link`.

## Procedure

Feishu pool:

```bash
python3 scripts/screen_feishu_pool.py --dry-run
python3 scripts/screen_feishu_pool.py
python3 scripts/list_feishu_pool.py
```

One URL without writes:

```bash
python3 scripts/screen_and_assign.py --url "<url>" --title "<title>"
```

Use `--no-fetch` only when body retrieval is unavailable and retain the lower
confidence reason. Reject or deprioritize thin campaign copy, partnerships,
awards, and sources without enough technical detail.

## Checks

- Do not force both accounts onto every source.
- Keep recommendations inside each account's fixed two subreddits.
- Use `Suitable` for normal drafting; use `Borderline` only after human review.
- Preserve screening reasons and scores as metadata, never draft prose.
