---
name: reddit-pool-sync
description: >
  Preview or sync unique published official Blog Post rows from Content All in
  One / All content into the Feishu Reddit Blog Pool with the 2026-01-01 cutoff. Use for
  "$reddit-pool-sync", "同步最新的pool", sync-source diagnostics, or checking
  which rows would be imported. Do not screen, draft, validate, or deliver Reddit
  content.
---

# Reddit Pool Sync

Run commands from the project root.

## Fixed Source

- Base: Zilliz Content All in One (`TXy3bCKznaz89fseyo3cPMShnyb`)
- Table: `All content` (`tblsyUaNiyPnhrFI`)
- View: `all content` (`vewx5CDVdU`)
- Category option: `Blog Post`
- Status option: `Published`
- Target: `Reddit Blog Pool` (`tbl3yFyNWxEdC9OT`)
- Normal cutoff: `2026-01-01`

The real Feishu option is `Blog Post`; treat the user phrase “Post Blog” as that
existing option. Do not use `Medium sync`, `Medium Daily`, or EN Content.

Require `Category = Blog Post`, `Status = Published`, a non-empty official
`/blog/` Publish URL, and a recoverable publish date. Deduplicate by canonical
URL. Sort eligible and new rows by publish date descending and report how many
fall inside the configured latest-7-day priority window.

## Procedure

Preview first, then run the same command without `--dry-run` only when an actual
sync is requested:

```bash
python3 scripts/sync_blog_pool_from_content_all_in_one.py --since-date 2026-01-01 --dry-run
python3 scripts/sync_blog_pool_from_content_all_in_one.py --since-date 2026-01-01
```

## Checks

- Confirm `source_view_id` is `vewx5CDVdU`.
- Confirm the source label contains `Category=Blog Post` and `Status=Published`.
- Confirm dry-run writes zero rows.
- Confirm `priority_window_days = 7`, and review `recent_eligible` and
  `recent_new` before syncing.
- Report new, already-present, not-published, missing-URL, non-official,
  old-date, and unknown-date counts.
- Do not change screening fields on existing pool rows.
