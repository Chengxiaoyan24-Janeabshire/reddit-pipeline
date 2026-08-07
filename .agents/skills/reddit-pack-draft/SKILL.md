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

1. hard anonymity, title, brand, link, and account/subreddit rules from
   `data/weekly_post_rules.json`;
2. stable account persona from `data/accounts.json` and its assigned fingerprint;
3. subreddit/Post Type overlay from Markdown and screenshots;
4. source-specific facts.

Source facts bound all factual claims at every layer. Persona guidance changes
how an allowed fact is framed; it never turns a source author's experience into
the anonymous account's personal history.

Screenshots never supply identity, employer, disclosure, links, typos, metrics,
or factual claims.

## Weekly Slots

Create exactly R1 → `r/Rag`, R1 → `r/AI_Agents`, R2 →
`r/vectordatabase`, and R2 → `r/LocalLLaMA`. Use `No fixed post type` for
`r/vectordatabase`. Prefer suitable ungenerated sources published within the
latest 7 days. Use older suitable sources only for slots that recent sources
cannot cover.

## Draft Rules

- Keep R1/R2 anonymous and `disclosure` empty.
- Allow `I built` only when the source supports the development background.
- Write every title from a first-person singular perspective, such as `I think`,
  `Now I believe`, or `What I learned`, or as an explicit opinion-seeking
  question ending in `?`. Do not use a fully third-person declarative title.
- Do not mention Milvus in the title. Mention Milvus exactly once in every body,
  using source-supported technical background or data, and fill
  `milvus_mention_basis` with a short evidence note. Make the mention indirect by
  positioning it as one example within a category or peer group, such as
  `vector databases like Milvus`, `data infrastructures such as Milvus`, or
  `Milvus and other databases`. Do not write direct product placement such as
  `Milvus handles...`, `use Milvus...`, or `if Milvus is...`. If the source
  cannot support a natural mention, replace the source.
- Never mention Zilliz.
- Set every item to `link_policy = no_link`; omit or empty `approved_link` and
  never place a URL in title/body.
- Preserve the account fingerprint; use screenshots only to adapt Post Type,
  opening structure, sectioning, and question shape.
- Realize shared language rules through the assigned fingerprint instead of
  repeating one template: R1 uses practical working judgments, lessons, or
  checklists; R2 uses production skepticism, workload limits, and decision
  criteria. Use the fingerprint's title, opening, buffer, and required-context
  guidance together.
- The first sentence must establish a source-supported first-person perspective.
  Do not delay the account voice or invent personal history to achieve this.
- Include at least one grammatical language buffer to calibrate a judgment or
  uncertainty, such as
  `probably`, `one concern I have`, `my current view`, `I suspect`, or
  `I would likely`. Keep them grammatical and sparse; do not hedge every
  sentence or weaken source-supported facts.
- Include concrete constraints and separate evidence from assumptions.
- End a `Tutorial` with the final takeaway, verification step, or next action;
  do not add a community question at the end.
- For a `Discussion`, an invitation to reply is optional. When used, keep it
  soft and conversational, such as `Would love to hear your thoughts.`, rather
  than ending on a sharp or interrogative question.
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
      "title": "What I learned about ...",
      "body": "...",
      "disclosure": "",
      "link_policy": "no_link",
      "milvus_mention_basis": "The source-supported reason for the single body mention.",
      "angle": "...",
      "length_tier": "standard_post"
    }
  ]
}
```

Return only final structured fields and draft content. Hand the result to
`$reddit-pack-validate` before any delivery.
