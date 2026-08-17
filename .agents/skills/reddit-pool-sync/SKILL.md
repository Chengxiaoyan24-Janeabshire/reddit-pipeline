---
name: reddit-pool-sync
description: >
  Preview or sync eligible official Blog rows from the currently configured
  source into the Feishu Reddit Blog Pool. Use for "$reddit-pool-sync",
  "同步最新的pool", sync-source diagnostics, or checking which rows would be
  imported. Do not screen, draft, validate, or deliver Reddit content.
---

# Reddit Pool Sync

Run commands from the project root.

## Required Context

Read:

- `guidance/reddit/workflow/source_sync.json` for the source IDs, category, status,
  cutoff, official hosts, and excluded sources;
- `guidance/reddit/workflow/weekly.json` for source-recency priority.

Do not copy these values into this Skill. Keep the stage procedure stable while
the external workflow values change independently.

Use the JSON files for normal execution. When the user asks to inspect the
rules, show `guidance/reddit/workflow/RULES.md`, the generated human review view. Do
not treat it as a second authority.

## Procedure

Preview first:

```bash
python3 scripts/sync_blog_pool_from_content_all_in_one.py --dry-run
```

Run the same command without `--dry-run` only when the user explicitly requests
the actual sync:

```bash
python3 scripts/sync_blog_pool_from_content_all_in_one.py
```

## Checks

- Confirm the configured Feishu source matches `source_sync.json`.
- Require the configured category, status, official URL shape, and recoverable
  publish date.
- Deduplicate canonical URLs and keep the configured recency ordering.
- Confirm dry-run writes zero rows.
- Report eligible, recent, new, existing, rejected, missing-date, and written
  counts using the current contract.
- Do not change screening fields on existing pool rows.
