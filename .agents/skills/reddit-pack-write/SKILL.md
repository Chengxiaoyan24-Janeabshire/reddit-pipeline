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

Require a pack accepted by `$reddit-pack-validate` under the current workflow
and guidance. Do not override current link, disclosure, brand, or metadata
policy during delivery.

## Procedure

Revalidate and preview:

```bash
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < packs.json
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < packs.json
```

Write only after both succeed and the user explicitly authorizes delivery:

```bash
python3 scripts/append_pack_to_feishu.py --weekly < packs.json
```

Omit `--weekly` for an approved partial pack. Stop after `--dry-run` when the
user requested only a preview.

## Output Contract

Create the current configured review document and structured Persona Pipeline
metadata, including `Source Chapter` and `partn` for R3 chapter-derived posts,
then update referenced pool counters where supported. Preserve the
validated content and skip optional fields that do not exist in the live Base.

## Safety Boundary

- Never write after failed validation or from preview-only intent.
- Never put reasoning, credentials, or private identity into review output.
- Never log in to Reddit or publish, comment, reply, vote, warm up accounts, or
  coordinate engagement.
