---
name: reddit-pack-validate
description: >
  Validate Reddit draft JSON for fixed weekly slots, R1/R2 boundaries, Post
  Types, stable fingerprints, anonymity, Milvus/Zilliz policy, no-link policy,
  length, duplicates, and optional discussion endings. Use for "$reddit-pack-validate",
  "检查 Reddit pack", or any review that must not write Feishu.
---

# Reddit Pack Validate

Run commands from the project root.

## Procedure

Weekly pack:

```bash
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < packs.json
```

For a single-source partial pack, omit `--weekly`. Never use `--allow-links`;
that option is retired.

## Required Checks

- Weekly mode contains exactly four unique configured slots.
- Only R1/R2 and their fixed subreddits appear.
- Every item has a valid Post Type.
- Disclosure is empty and no identity, employer, contributor/maintainer role,
  or affiliation is revealed.
- The title contains no Milvus. The body contains Milvus zero or one time. A
  single mention requires non-empty `milvus_mention_basis`.
- Zilliz never appears.
- `link_policy` is `no_link`, `approved_link` is empty, and title/body contain no
  URL.
- Bodies are nonempty and unique, with a valid length tier and allowed code.
- A question ending is optional and must not create an error or warning by
  itself.
- Review warnings for Post Type mismatch or unusual length; do not discard
  warnings silently.

## Safety Boundary

Always use `--validate-only`. Never create Docs, write rows, update pool counts,
append CSV output, or perform Reddit activity.
