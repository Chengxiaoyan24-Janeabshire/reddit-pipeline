# Reddit Pipeline

## Purpose

Generate a fixed four-slot weekly Reddit content pack from recent official blog
ideas, then parse Reddit JSON that a human has pasted into Feishu for published
post review. The pipeline creates drafts and review metadata; it never performs
Reddit account activity or fetches Reddit JSON itself.

## Skills

Use the repo-scoped `$reddit-weekly` Skill for the complete workflow. Use a
stage Skill when the user wants only one step:

- `$reddit-pool-sync`: preview or sync eligible source rows only;
- `$reddit-source-screen`: screen and assign sources only;
- `$reddit-pack-draft`: produce draft JSON only;
- `$reddit-pack-validate`: validate only, with no writes;
- `$reddit-pack-write`: preview or write validated drafts to Feishu review.
- `$reddit-json-content-parse`: parse pasted `Reddit JSON Content`, then preview
  or update published-post metrics, status, comment summaries,
  public-opinion alerts, and Milvus signals.

All seven Skills live under `.agents/skills/`. Run their scripts from the project
root with `python3 scripts/...`.

## Source and weekly contract

- Sync only from Content All in One / `All content` / `all content`
  (`TXy3bCKznaz89fseyo3cPMShnyb` / `tblsyUaNiyPnhrFI` / `vewx5CDVdU`).
- Require `Category = Blog Post`, `Status = Published`, an official `/blog/`
  URL, a recoverable publish date, and a date on or after `2026-01-01`.
- Prefer suitable, ungenerated sources published within the latest 7 days.
  If they cannot cover all four weekly slots, fill the remaining slots from
  older suitable sources in descending publish-date order.
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
- Titles cannot mention Milvus. Every body must mention Milvus exactly once when
  the source supports the technical background or data; fill
  `milvus_mention_basis`. Replace a source that cannot support the required
  mention.
- Generated content cannot mention Zilliz.
- R1/R2 are always `no_link`; reject URLs and `approved_link`.
- Open with a source-supported first-person setup and use sparse, grammatical
  language buffers for judgments or uncertainty; do not invent personal history
  or hedge source-supported facts.
- Tutorials must not end with a question. Discussion reply invitations are
  optional and, when used, should be soft and conversational rather than a hard
  interrogative ending.
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
- `scripts/reddit_json_content.py`: pasted Reddit JSON parsing, status,
  approximate downvotes, comment triage, and Feishu parsing field contract.

Draft delivery outputs contain only final draft content and structured review
fields. JSON-content parsing dry-runs may include sanitized comment samples without
Reddit author usernames or links so a human can review the summary; Feishu
receives only the summary, metrics, status, alerts, and signals. Do not write
reasoning, scratch notes, credentials, or private account details into output.

## Feishu workflow

Preview writes before executing them:

```bash
python3 scripts/sync_blog_pool_from_content_all_in_one.py --since-date 2026-01-01 --dry-run
python3 scripts/screen_feishu_pool.py --dry-run
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < packs.json
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < packs.json
python3 scripts/parse_reddit_json_content.py --from-feishu --snapshot-out packs/reddit-json-content-preview.json
```

Live writes are allowed only when the user explicitly requests the matching
sync, screening, delivery, or JSON-content parsing step. Reddit publishing remains manual
and is tracked in `Reddit Persona Pipeline` with `Status`, `Publish URL`,
`Publish Date`, and `Publisher`.

Published-post parsing reads only the complete JSON text a human pasted into
`Reddit JSON Content`. It never opens Reddit, generates a URL, or performs
Reddit account activity. Never overwrite `Reddit JSON` or `Reddit JSON Content`.
Reddit does not expose exact public downvotes; store only the explicitly labeled
`Downvotes (Estimated)` value. Set `Status = Cancel` only when valid pasted JSON
proves the post is removed or deleted; do not cancel on locks, archives, deleted
authors, empty content, or invalid JSON. Every live parse write must use the
exact dry-run snapshot and must fail closed if the Feishu target set, JSON
content hash, or field plan changed after preview.

## Change Log

Update `CHANGELOG.md` in every GitHub push that changes behavior, rules, or user
workflow. Use a `YYYY-MM-DD — short topic` heading and only the applicable
`Added`, `Changed`, `Fixed`, `Removed`, or `Security` sections. Describe user or
runtime outcomes, not a file-by-file activity log.
