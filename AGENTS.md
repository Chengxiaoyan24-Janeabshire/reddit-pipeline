# Reddit Pipeline

## Purpose

Generate the currently configured weekly Reddit draft pack from recent official blog
ideas, deliver approved drafts to Feishu review, and monitor recently published
posts through visible Chrome/Browser page state. The project never performs
Reddit account activity or uses Reddit JSON/API responses.

## Progressive disclosure

Load only the context required by the active stage, in this order:

1. the latest user direction and this file;
2. the selected Skill under `.agents/skills/`;
3. current workflow values from `guidance/reddit/workflow/`;
4. shared editorial policy from `guidance/reddit/editorial/` when the stage edits or
   validates content;
5. only the selected subreddit rule JSON under `reference/slots/`;
6. only the selected account and audience rows under `reference/accounts/` and
   `reference/topic_bank.json`;
7. visual evidence from `resource/reddit/` only when screenshots are needed;
8. source-specific facts.

Workflow guidance controls weekly quantity, active accounts, slot assignment,
recency, and sync source. These execution values are not an editorial override.
Resources never define rules. Source facts bound all claims.

## Machine rules and review views

- JSON files under `guidance/` and `reference/` are the authoritative machine
  contracts used by scripts and AI workflow stages.
- Generated `RULES.md` and `TOPIC_RULES.md` files are human-readable review
  views. Load them when the user asks to inspect rules; do not use them as a
  second runtime authority.
- Never maintain JSON and MD independently. Change the JSON, then run
  `python3 scripts/render_rule_docs.py`.
- Run `python3 scripts/render_rule_docs.py --check` before handoff. A stale or
  missing MD review view is a validation failure.

## Editorial instruction precedence

For screening, drafting, rewriting, and validation, resolve editorial choices
in this exact order:

1. **Guidance**: satisfy disclosure first, then the required first-person `I`
   framing and grammatical language Buffer. All other global anonymity, brand,
   link, title, opening, and safety rules remain mandatory here.
2. **Subreddit**: obey the selected community's subrules, select only a valid
   configured Post Category/Post Type, then apply common native post structures
   and writing style.
3. **Audience angle**: choose the preferred technical angle, topic realization,
   and account fingerprint only from the options left by the first two levels.
   Vector-database and retrieval interests are examples of this layer.

Higher levels always win. If a Subreddit choice conflicts with Guidance, reject
or replace the Subreddit choice. If an audience angle or fingerprint conflicts
with either higher level, choose another angle; it cannot relax the higher
rule. If no compliant lower-level choice remains, reject the source or draft.
Source facts are a non-negotiable factual boundary at every level and can never
be invented to satisfy an angle.

## Layer stability

Do not rank `guidance/`, `reference/`, and `resource/` by expected modification
frequency; all three are working content layers and may change often. Keep the
base calling logic under `.agents/skills/` stable unless the workflow stages,
commands, outputs, or write gates actually change. This maintenance guidance
does not alter the editorial instruction precedence above.

## Skills

Use `$reddit-weekly` for the complete workflow. Use one stage Skill when the
user requests only that stage:

- `$reddit-pool-sync`: preview or sync eligible official Blog rows;
- `$reddit-source-screen`: screen and assign sources;
- `$reddit-pack-draft`: generate draft JSON only;
- `$reddit-pack-validate`: validate without writes;
- `$reddit-pack-write`: preview or write validated drafts to Feishu review;
- `$reddit-browser-monitor`: inspect visible published-post state and preview or
  write monitoring fields.

All seven Skills live under `.agents/skills/`. Run runtime commands from the
project root with `python3 scripts/...`.

## Sources of truth

- `guidance/reddit/workflow/weekly.json`: weekly quantity, active accounts, source
  recency, slot assignment, and Post Types;
- `guidance/reddit/workflow/source_sync.json`: current sync source and eligibility
  contract;
- `reference/accounts/`: account persona, topic routing, and fingerprints;
- `reference/slots/`: four machine-readable slot rules and generated Markdown
  reviews, plus the community registry;
- `reference/topic_bank.json`: shared screening taxonomy;
- `guidance/reddit/editorial/editorial_policy.json`: global editorial and safety checks;
- `guidance/reddit/editorial/content_length_rules.json`: length and code tiers;
- `guidance/reddit/editorial/RULES.md`: generated human review of Editorial JSON;
- `guidance/reddit/workflow/RULES.md`: generated human review of Workflow JSON;
- `reference/accounts/RULES.md`: generated human review of account JSON;
- `reference/TOPIC_RULES.md`: generated human review of topic-bank JSON;
- `reference/slots/RULES.md`: generated human review of slot-registry JSON;
- `resource/reddit/`: non-authoritative screenshots and generated PDFs;
- `config/`: Feishu IDs and field mappings without credentials;
- `scripts/resource_paths.py`: authoritative local resource path map.

## Safety and write gates

- Never automate Reddit login, posting, comments, replies, voting, likes,
  warm-up activity, messages, follows, reports, or coordinated engagement.
- Never use Reddit `.json` URLs, APIs, network-response bodies, cookies, local
  storage, or session files.
- Preview every Feishu mutation first. Perform the matching live sync,
  screening, delivery, or monitoring write only after explicit user approval.
- Browser monitoring uses only visible page state and never overwrites
  `Impression (7 days)` or publication `Status`.
- Output only final drafts and structured review fields. Never persist reasoning,
  raw comments, Reddit usernames, comment links, credentials, or private account
  data.

## Standard previews

```bash
python3 scripts/sync_blog_pool_from_content_all_in_one.py --dry-run
python3 scripts/screen_feishu_pool.py --dry-run
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < packs.json
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < packs.json
python3 scripts/reddit_browser_monitor.py --list-targets
python3 scripts/render_rule_docs.py --check
```

## Change Log

Update `CHANGELOG.md` in every GitHub push that changes behavior, rules, or user
workflow. The entire Change Log must use Simplified Chinese. Use a
`YYYY-MM-DD — 中文主题` heading and only the applicable `新增`、`变更`、`修复`、
`移除` or `安全` sections. Describe user or runtime outcomes rather than a file
activity log.
