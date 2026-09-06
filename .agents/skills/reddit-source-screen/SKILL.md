---
name: reddit-source-screen
description: >
  Screen pending Reddit Blog Pool rows or one supplied blog URL for technical
  suitability, current account/slot assignment, Post Type, and topic fit. Use
  for "$reddit-source-screen", "筛选 Reddit pool", or checking whether one source
  fits the current Reddit lanes. Do not draft or deliver content.
---

# Reddit Source Screen

Run commands from the project root.

## Required Context

Read:

- `guidance/reddit/workflow/weekly.json` for active accounts, slot assignment, and
  recency;
- `guidance/reddit/editorial/editorial_policy.json` for current global eligibility
  boundaries and the mandatory instruction precedence;
- the selected JSON under `reference/slots/` for Subreddit subrules, valid
  Post Category/Post Type, native structure, and style;
- only the selected rows from `reference/accounts/account_topic_rules.json` and
  `reference/topic_bank.json` for lower-priority audience-angle matching.

Use JSON for normal execution. If the user asks to inspect rules, use the
generated `RULES.md`, `TOPIC_RULES.md`, and selected slot Markdown review views;
do not load them as duplicate runtime authorities.

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
confidence reason. Run the live Feishu screening command only after explicit
authorization.

## Checks

- Do not force every active account onto every source.
- Keep recommendations inside the current account/slot mapping. R3 may use all
  four physical Subreddit slots; R1 and R2 retain their original two-slot
  ownership when R3 does not replace them.
- Apply current recency ordering before older fallback sources.
- Reject a non-James pool row with `已生成内容数 > 0`. Keep James Luan rows
  eligible while their consecutive chapter series still has uncovered source
  sections. The summary-share mode may be used at most once per source URL;
  generated James content must never restart or reuse a completed chapter part.
- Apply editorial choices in this order: Guidance first; selected Subreddit
  subrules and Category/Post Type second; audience-preferred angle, topic fit,
  and fingerprint third.
- Reject a source that cannot support Guidance. If an audience-preferred angle
  conflicts with Guidance or the Subreddit, choose another compliant angle; do
  not weaken either higher level.
- Treat source facts as a boundary at every level. Never invent facts to make a
  source fit a lane or angle.
- Preserve suitability, reasons, scores, topics, accounts, slots, Post Types,
  source author, available author rewrite modes, and current conditional link
  policy as metadata; never draft prose in this stage. Route a James Luan source
  only to R3. When `已生成内容数 > 0`, expose only chapter mode; summary-share is
  available only while the count is zero. Never assign a James
  source to R1/R2, and never assign a non-James source to R3.
