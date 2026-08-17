# Reddit Weekly Pipeline

This project produces policy-compliant Reddit drafts for human review and manual
publishing, then monitors already-published posts through visible
Chrome/Browser page state. It never performs Reddit account activity.

## Workflow

```text
Content All in One / All content / all content
  -> pool sync
  -> source screening and R1/R2 assignment
  -> four-slot drafting
  -> validation
  -> Feishu review delivery
  -> human review and manual Reddit publishing
  -> visible-page browser monitoring for posts up to 14 days old
```

The current pack size, active accounts, and account/subreddit slots are loaded
from `guidance/reddit/workflow/weekly.json`; they are intentionally not duplicated in
this README.

## Progressive resource layout

| Layer | Responsibility |
|---|---|
| `guidance/reddit/workflow/` | Machine JSON plus generated MD review for quantity, assignment, recency, and sync |
| `guidance/reddit/editorial/` | Machine JSON plus generated MD review for global editorial and length rules |
| `reference/accounts/` | Machine JSON plus generated MD review for angle, routing, and fingerprints |
| `reference/slots/` | Machine JSON plus generated MD review for each Subreddit slot and registry |
| `guidance/reddit/*.md` | Human-authored operating guidance, FAQ, and examples |
| `resource/reddit/` | Non-authoritative screenshots and generated PDFs |
| `.agents/skills/` | Stable stage routing, commands, outputs, and write gates |
| `scripts/` | Runtime commands and shared implementation modules |

Supporting directories remain separate:

- `config/`: Feishu table IDs, field mappings, and credential template;
- `samples/`: valid input examples, not policy;
- `tests/`: regression coverage;
- `packs/` and `tmp/`: ignored outputs and temporary files.

`guidance/`, `reference/`, and `resource/` are all active content layers and may
change regularly. `.agents/skills/` contains the comparatively stable stage
calling logic and changes only when workflow stages, commands, outputs, or write
gates change. This is a maintenance boundary, not a content-rule priority.

When content rules interact, apply `Guidance > Subreddit > Audience angle`:
global Disclosure and language requirements first; subreddit subrules, valid
Category/Post Type, and native style second; preferred technical angles and
account fingerprints third. Higher levels always win, while source facts
constrain every level.

## Rule file formats

Rule configuration has two synchronized surfaces:

- **JSON** is the bottom machine contract read by AI workflow stages and Python
  validators.
- **Markdown** is the top review surface intended for human inspection.

The Markdown views are generated, not independently edited. After a JSON rule
change, run `python3 scripts/render_rule_docs.py`; use `--check` to fail when a
review page is stale. Start with [Editorial rules](guidance/reddit/editorial/RULES.md),
[Workflow rules](guidance/reddit/workflow/RULES.md),
[Account rules](reference/accounts/RULES.md),
[Topic rules](reference/TOPIC_RULES.md), or
[Subreddit registry](reference/slots/RULES.md).

Read [reference/README.md](reference/README.md),
[guidance/reddit/README.md](guidance/reddit/README.md),
[resource/reddit/README.md](resource/reddit/README.md), and
[scripts/README.md](scripts/README.md) only when that layer is needed.

## Skills

| Skill | Result |
|---|---|
| `reddit-weekly` | Complete four-slot workflow |
| `reddit-pool-sync` | Source-pool preview or authorized sync |
| `reddit-source-screen` | Source suitability and lane assignment |
| `reddit-pack-draft` | Draft JSON without writes |
| `reddit-pack-validate` | Read-only validation |
| `reddit-pack-write` | Feishu review preview or authorized write |
| `reddit-browser-monitor` | Visible metrics and comment-signal preview or authorized write |

Each Skill loads only the current workflow guidance, relevant editorial guidance,
selected account, selected slot, and optional visual resources it needs. Runtime
validation merges `guidance/reddit/workflow/weekly.json` with
`guidance/reddit/editorial/editorial_policy.json` and fails closed if the three-level
instruction contract is reordered or reassigned.

## Source contract

`guidance/reddit/workflow/source_sync.json` owns the current source IDs, category,
status, URL boundary, minimum date, and excluded sources. Source recency and
older-source fallback behavior live in `guidance/reddit/workflow/weekly.json`.

## Draft JSON

```json
{
  "source_title": "...",
  "source_url": "https://official-source.example/blog/...",
  "pool_record_id": "rec...",
  "items": [
    {
      "account_code": "<configured account>",
      "content_type": "technical_post",
      "subreddit": "<configured subreddit>",
      "post_type": "<configured Post Type>",
      "title": "...",
      "body": "...",
      "disclosure": "",
      "link_policy": "<guidance value>",
      "milvus_mention_basis": "<when required by guidance>",
      "angle": "...",
      "voice_fingerprint": "<configured fingerprint>",
      "length_tier": "<configured tier>"
    }
  ]
}
```

`source_url` is internal review metadata. Generated content follows the current
link and brand guidance in `guidance/reddit/`.

## Setup and verification

```bash
bash scripts/setup.sh
python3 -m unittest
python3 scripts/render_rule_docs.py --check
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < samples/weekly_pack.example.json
```

## Common previews

```bash
# Source sync
python3 scripts/sync_blog_pool_from_content_all_in_one.py --dry-run

# Screening
python3 scripts/screen_feishu_pool.py --dry-run

# One-source screening without writes
python3 scripts/screen_and_assign.py --url "https://milvus.io/blog/example" --title "Example" --no-fetch

# Validation and delivery preview
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < samples/weekly_pack.example.json
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < samples/weekly_pack.example.json

# Published-post monitoring targets
python3 scripts/reddit_browser_monitor.py --list-targets
```

Feishu live writes require explicit approval. Reddit publishing and engagement
always remain manual.

## Change Log

Update `CHANGELOG.md` with each GitHub push that changes behavior, rules, or
user workflow. Entries describe outcomes rather than listing modified files.
