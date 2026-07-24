---
name: reddit-pack-write
description: >
  Preview or write a previously validated Reddit pack into Feishu Content Docs
  and Reddit Persona Pipeline review rows. Use for "$reddit-pack-write" or an
  explicit request to preview, save, append, or submit approved drafts. Never
  publish or interact on Reddit.
---

# Reddit Pack Write

Run commands from the project root.

## Input Contract

Require a pack already accepted by `$reddit-pack-validate`. R1/R2 are both
no-link, so never use `--allow-links` and never deliver an `approved_link`.

## Procedure

Revalidate and preview:

```bash
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < packs.json
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < packs.json
```

Write only after both succeed and the user authorized delivery:

```bash
python3 scripts/append_pack_to_feishu.py --weekly < packs.json
```

Omit `--weekly` for an approved partial pack. Stop after `--dry-run` when the
user asked only for preview.

## Output Contract

Create one URL-free Content Doc per draft, write structured review metadata to
`Reddit Persona Pipeline`, and increment referenced pool counts. Store
`milvus_mention_basis` in review metadata when present; do not append links.

## Safety Boundary

- Never write after failed validation or from preview-only intent.
- Never put reasoning, credentials, or private identity into review output.
- Never log in to Reddit or publish, comment, reply, vote, warm up accounts, or
  coordinate engagement.
