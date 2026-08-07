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
- Each account uses its configured `voice_fingerprint`; a known fingerprint from
  the other account is still invalid.
- Every item has a valid Post Type.
- Disclosure is empty and no identity, employer, contributor/maintainer role,
  or affiliation is revealed.
- The title contains no Milvus and either uses a first-person singular
  perspective or is an explicit question ending in `?`; fully third-person
  declarative titles fail validation.
- The body contains Milvus exactly once, requires non-empty
  `milvus_mention_basis`, and phrases the mention indirectly as a category
  example or peer-group member. Direct product placement fails validation.
- Zilliz never appears.
- `link_policy` is `no_link`, `approved_link` is empty, and title/body contain no
  URL.
- A Tutorial does not end with a question. A Discussion that ends with a hard
  question receives a review warning; a soft invitation is allowed.
- The first sentence establishes a source-supported first-person perspective,
  and every body contains at least one grammatical language buffer attached to
  a judgment or uncertainty. Missing either fails validation. Buffers must not
  weaken source-supported facts, benchmark setup, or measurements.
- Bodies are nonempty and unique, with a valid length tier and allowed code.
- Review warnings for Post Type mismatch or unusual length; do not discard
  warnings silently.

The machine validator can enforce the account-to-fingerprint mapping and shared
language signals, but it cannot fully prove that prose sounds like R1 rather
than R2. Human review must still compare the title, opening, language buffers,
and required technical example against `data/user_fingerprints.json`.

## Safety Boundary

Always use `--validate-only`. Never create Docs, write rows, update pool counts,
append CSV output, or perform Reddit activity.
