# Reddit Pipeline

## Purpose

Generate a fixed four-slot weekly Reddit content pack from recent official blog
ideas. The pipeline creates drafts for human review and manual publishing; it
never performs Reddit account activity.

## Skills

Use the repo-scoped `$reddit-weekly` Skill for the complete workflow. Use a
stage Skill when the user wants only one step:

- `$reddit-pool-sync`: preview or sync eligible source rows only;
- `$reddit-source-screen`: screen and assign sources only;
- `$reddit-pack-draft`: produce draft JSON only;
- `$reddit-pack-validate`: validate only, with no writes;
- `$reddit-pack-write`: preview or write validated drafts to Feishu review.

All six Skills live under `.agents/skills/`. Run their scripts from the project
root with `python3 scripts/...`.

## Source and weekly contract

- Sync only from Content All in One / `All content` / `all content`
  (`TXy3bCKznaz89fseyo3cPMShnyb` / `tblsyUaNiyPnhrFI` / `vewx5CDVdU`).
- Require `Category = Blog Post`, `Status = Published`, an official `/blog/`
  URL, a recoverable publish date, and a date on or after `2026-01-01`.
- Do not use Medium Sync, Medium Daily, EN Content, or the retired calendar
  view.
- Generate exactly four weekly slots: R1 → `r/Rag`, R1 → `r/AI_Agents`, R2 →
  `r/vectordatabase`, and R2 → `r/LocalLLaMA`.
- Use `No fixed post type` for `r/vectordatabase`; every other item must use a
  configured subreddit Post Type.

## Editorial and safety rules

- R1/R2 are anonymous, use empty disclosure, and never reveal identity,
  employer, affiliation, contributor/maintainer status, or private account data.
- `I built` is allowed only when supported by the source and without inventing
  personal history, customers, benchmarks, metrics, or results.
- Titles cannot mention Milvus. A body may mention Milvus once when the source
  supports the technical background or data; fill `milvus_mention_basis`.
- Generated content cannot mention Zilliz.
- R1/R2 are always `no_link`; reject URLs and `approved_link`.
- Open community questions are optional. Preserve one when it fits; do not
  force a question ending.
- Keep all four length tiers: `short_post`, `standard_post`, `long_post`, and
  `code_long_post`. Use `short_post` only for genuinely concise content.
- Screenshots provide Post Type and structural overlays only. Never copy their
  identity, employer, disclosure, links, typos, metrics, or claims.
- Never automate Reddit login, posting, comments, replies, voting, likes,
  warm-up activity, or coordinated engagement.

## Sources of truth

- `data/weekly_post_rules.json`: active accounts, fixed slots, Post Types,
  anonymity, brand, question, and link policy.
- `data/accounts.json` and `data/user_fingerprints.json`: stable personas and
  voice boundaries.
- `data/account_topic_rules.json` and `data/topic_bank.json`: screening and
  advisory topic matching; they cannot create new account/subreddit permission.
- `data/content_length_rules.json`: the four length and code tiers.
- `reference/subreddit_rule/`: sanitized community guidance and screenshots.
- `reference/*.md`: editable Reference content; corresponding PDFs are generated
  deliverables.

Pipeline outputs contain only final draft content and structured review fields.
Do not write reasoning, scratch notes, credentials, or private account details
into output.

## Feishu workflow

Preview writes before executing them:

```bash
python3 scripts/sync_blog_pool_from_content_all_in_one.py --since-date 2026-01-01 --dry-run
python3 scripts/screen_feishu_pool.py --dry-run
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < packs.json
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < packs.json
```

Live writes are allowed only when the user explicitly requests the matching
sync, screening, or delivery step. Reddit publishing remains manual and is
tracked in `Reddit Persona Pipeline` with `Status`, `Publish URL`, `Publish
Date`, and `Publisher`.

## Change Log

Update `CHANGELOG.md` in every GitHub push that changes behavior, rules, or user
workflow. Use a `YYYY-MM-DD — short topic` heading and only the applicable
`Added`, `Changed`, `Fixed`, `Removed`, or `Security` sections. Describe user or
runtime outcomes, not a file-by-file activity log.
