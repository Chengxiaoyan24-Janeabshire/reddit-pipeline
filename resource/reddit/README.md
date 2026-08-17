# Reddit Resources

Resources are non-authoritative visual or generated files. They support drafting
and review but never define policy.

- `slots/`: sanitized subreddit screenshots used only for Post Type and native
  structure overlays.
- `pdfs/`: generated copies of the Markdown guidance for distribution.

Editable rules live in `guidance/reddit/`. Dynamic weekly, sync, account, topic,
and slot choices live in `reference/`.

Rebuild PDFs with `python3 scripts/rebuild_reddit_resources.py` after editing the
corresponding Markdown under `guidance/reddit/`.
