---
name: reddit-pack-validate
description: >
  Validate Reddit draft JSON against the current workflow, global guidance,
  account fingerprints, slot/Post Type overlays, length rules, and duplicate
  checks. Use for "$reddit-pack-validate", "检查 Reddit pack", or any review that
  must not write Feishu.
---

# Reddit Pack Validate

Run commands from the project root.

## Required Context

Validation combines:

- `guidance/reddit/editorial/editorial_routes.json`, followed by only the matched
  Guidance/Reference/Resource route;
- `guidance/reddit/workflow/weekly.json`;
- `guidance/reddit/editorial/editorial_policy.json`;
- `guidance/reddit/editorial/content_length_rules.json`;
- the selected `reference/slots/` JSON;
- the selected account and topic rows under `reference/accounts/` and
  `reference/topic_bank.json`.

Do not duplicate their current values in this Skill.

Validate against JSON. Use generated Markdown review views only when the user
asks to inspect the rules, never as a separate validation authority.

## Procedure

Configured weekly pack:

```bash
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < packs.json
```

For a genuine partial pack, omit `--weekly`.

## Required Checks

- Resolve `source_author` through the route manifest before selecting a validator. A James Luan source uses
  the separate disclosed-author validator and must never fall through to the
  anonymous validator.
- For James, require account R3, the complete James/Zilliz/Milvus identity
  framing, and exactly one configured `author_rewrite_mode`. A weekly pack must
  contain exactly three James posts, with exactly one using
  `r3_article_summary_share`. The summary-share post must recap the full article
  throughline before its original link. Chapter mode must
  include `source_chapter` and a source-local `partn` value matching `part1`,
  `part2`, and so on without gaps or reuse; cover one coherent chapter-level argument, preserve
  its reasoning, and supply enough prerequisite context to stand alone. It must
  begin with identity, transition naturally into the next uncovered consecutive
  section, and continue through later parts without gaps or reuse until the whole
  source is covered. Summary-share may be used at most once per source URL.
  Do not enforce other anonymous title/question,
  first-sentence `I`, Buffer, R2 question quota, Milvus placement, competitor,
  brand, anonymity, or no-link checks.
- For non-James sources, enforce the full anonymous Guidance contract:
  first-person `I`, grammatical language Buffer, anonymity, brand mentions,
  links, title, opening, closing, length/code tiers, and prohibited content.
- Reject James drafts on R1/R2 and reject non-James drafts on R3.
- For James summary-share only, require `approved_link == source_url`, require
  that exact URL once in its own body paragraph, and reject any additional URL.
  Chapter mode and anonymous routes keep their configured no-link body policy.
  For every route, require delivery to expose `source_url` in Feishu `原文`.
- Enforce the selected Subreddit second: community subrules, a valid configured
  Post Category/Post Type, native structure, and style.
- Enforce the audience layer third: topic/angle fit and the configured
  account-to-fingerprint mapping. An audience angle can never excuse a Guidance
  or Subreddit error.
- Enforce the current pack size, active accounts, and unique slots as workflow
  configuration outside the editorial precedence.
- For non-James R2 content, when `r2_short_question_policy` is enabled, require exactly one R2 short
  question-type post per weekly pack, using the configured question Post Type,
  `short_post` length, and an explicit question title.
- Reject empty or duplicate bodies and invalid structured fields.
- Report warnings for advisory Post Type, length, or ending mismatches.
- Human review still checks source support and whether the prose realizes the
  selected account fingerprint naturally.

If the layers conflict, the higher layer wins. Reject the draft when no
compliant lower-level alternative remains, and never invent source facts to
make an angle pass.

## Safety Boundary

Always use `--validate-only`. Never create Docs, write rows, update pool counts,
or perform Reddit activity.
