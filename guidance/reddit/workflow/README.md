# Workflow Guidance

These are the current machine-readable rules for how the workflow runs.

- `weekly.json`: active accounts, weekly pack size, source-recency behavior,
  account/subreddit assignment, Post Types, and slot resource pointers.
- `source_sync.json`: source Base/table/view, eligibility fields, minimum date,
  official hosts, URL prefix, and excluded sources.
- `RULES.md`: generated human-readable review of both workflow JSON files.

Changing these files should not require editing a Skill unless the stages,
commands, outputs, or write gates themselves also change. Runtime loaders and
tests consume them directly. Update samples when a changed weekly shape makes a
checked-in example obsolete. AI and scripts read JSON; humans review
`RULES.md`. Regenerate it with `python3 scripts/render_rule_docs.py` after every
rule change.
