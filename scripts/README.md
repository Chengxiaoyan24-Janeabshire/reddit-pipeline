# Runtime Scripts

Run commands from the project root with `python3 scripts/...`.

## Workflow commands

- `sync_blog_pool_from_content_all_in_one.py`: preview or sync source rows.
- `screen_feishu_pool.py`: screen pending Feishu pool rows.
- `screen_and_assign.py`: screen one source or provide the screening engine.
- `append_pack.py`: validate draft JSON without external writes.
- `append_pack_to_feishu.py`: validate, preview, or write review drafts.
- `reddit_browser_monitor.py`: validate browser observations and preview or
  write published-post monitoring fields.
- `list_feishu_pool.py`: inspect current pool rows.

## Setup and maintenance

- `setup.sh`: create the local runtime environment.
- `setup_feishu_tables.py`: create or reconcile Feishu tables.
- `render_rule_docs.py`: generate or check human-readable Markdown review
  views from the machine JSON under `guidance/` and `reference/`.
- `rebuild_reddit_resources.py`: render Markdown from `guidance/reddit/` into
  PDFs under `resource/reddit/pdfs/`.

## Shared runtime modules

- `resource_paths.py`: the only authoritative filesystem path map.
- `weekly_post_rules.py`: weekly policy loader and helpers.
- `feishu_client.py`, `feishu_docs.py`: Feishu transport and document helpers.
- `official_blog_catalog.py`, `fetch_blog.py`: official blog metadata and body
  retrieval helpers.
