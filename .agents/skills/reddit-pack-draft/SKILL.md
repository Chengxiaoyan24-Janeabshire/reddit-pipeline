---
name: reddit-pack-draft
description: >
  Turn screened technical sources into Reddit-native JSON drafts for the fixed
  R1/R2 lanes, either the four-slot weekly pack or a genuine smaller fit for one
  source. Use for "$reddit-pack-draft", "起草 Reddit pack", or revising Reddit
  draft JSON. Produce drafts only; do not write Feishu or Reddit.
---

# Reddit Pack Draft

Run shared tooling from the project root.

## Required Context

Read:

- `data/accounts.json`
- `data/account_topic_rules.json`
- `data/content_length_rules.json`
- `data/user_fingerprints.json`
- `data/weekly_post_rules.json`
- the selected slot's `reference_markdown` and screenshots

Apply precedence in this order:

1. hard anonymity, brand, link, and account/subreddit rules;
2. stable account persona and fingerprint;
3. subreddit/Post Type overlay from Markdown and screenshots;
4. source-specific facts.

Screenshots never supply identity, employer, disclosure, links, typos, metrics,
or factual claims.

## Weekly Slots

Create exactly R1 → `r/Rag`, R1 → `r/AI_Agents`, R2 →
`r/vectordatabase`, and R2 → `r/dataengineering`. Use `No fixed post type` for
`r/vectordatabase`.

## Draft Rules

- Keep R1/R2 anonymous and `disclosure` empty.
- Allow `I built` only when the source supports the development background.
- Do not mention Milvus in the title. Mention Milvus at most once in the body,
  only when the technical background or data is source-supported. When used,
  fill `milvus_mention_basis` with a short evidence note.
- Never mention Zilliz.
- Set every item to `link_policy = no_link`; omit or empty `approved_link` and
  never place a URL in title/body.
- Preserve the account fingerprint; use screenshots only to adapt Post Type,
  opening structure, sectioning, and question shape.
- Include concrete constraints and separate evidence from assumptions.
- Keep an open community question when it fits naturally; a question ending is
  optional and must not be forced.
- Use `short_post` for a genuine concise Discussion or Resource Request; retain
  `standard_post` for normal technical discussions and do not pad short posts.
- Do not invent experience, customers, benchmarks, metrics, or results.

## Output Shape

```json
{
  "source_title": "...",
  "source_url": "https://source.example/...",
  "pool_record_id": "rec...",
  "items": [
    {
      "account_code": "R1",
      "content_type": "technical_post",
      "subreddit": "r/Rag",
      "post_type": "Discussion",
      "title": "...",
      "body": "...",
      "disclosure": "",
      "link_policy": "no_link",
      "milvus_mention_basis": "",
      "angle": "...",
      "length_tier": "standard_post"
    }
  ]
}
```

Return only final structured fields and draft content. Hand the result to
`$reddit-pack-validate` before any delivery.
