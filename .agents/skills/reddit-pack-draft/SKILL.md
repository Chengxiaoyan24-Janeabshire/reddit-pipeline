---
name: reddit-pack-draft
description: >
  Turn screened technical sources into Reddit-native JSON drafts for the
  currently configured weekly accounts and slots, or a genuine smaller fit for
  one source. Use for "$reddit-pack-draft", "起草 Reddit pack", or revising
  Reddit draft JSON. Produce drafts only; do not write Feishu or Reddit.
---

# Reddit Pack Draft

Run shared tooling from the project root.

## Required Context

Read only what the selected source and slot require:

- `guidance/reddit/workflow/weekly.json` for current pack size, slot mapping,
  and the configured R2 short-question quota;
- `guidance/reddit/editorial/editorial_policy.json` and
  `guidance/reddit/editorial/content_length_rules.json` for the first-level global
  pass/fail rules;
- `guidance/reddit/editorial/editorial_routes.json` first, then only the selected
  route's Guidance, Reference, and Resource manifest;
- the selected slot JSON under `reference/slots/` for second-level
  Subreddit subrules, valid Category/Post Type, native structure, and style;
- the selected account and topic rows under `reference/accounts/` and
  `reference/topic_bank.json` for third-level audience angle and fingerprint;
- the selected screenshots under `resource/reddit/slots/` only when visual
  structure evidence is useful.

Use JSON for normal execution. Generated `RULES.md`, `TOPIC_RULES.md`, and slot
Markdown files are for human inspection only and must not become a second rule
source.

Apply the current user direction first. Source facts bound every factual claim.
For editorial choices, Guidance overrides the selected Subreddit, and the
selected Subreddit overrides the audience angle and account fingerprint. Resources
never create rules or claims.

## Procedure

1. Resolve the current target slots from `guidance/reddit/workflow/weekly.json`.
2. Select a suitable screened source for each requested slot using configured
   recency and fallback behavior.
3. Resolve `source_author` through `editorial_routes.json` before loading route
   content. Never load both route-specific Guidance/Reference/Resource chains.
   When `source_author` is James Luan, use only the configured disclosed-author
   route. Open the body in James's voice and identify him as James, CTO of
   Zilliz; explain that Zilliz is the company and builder behind Milvus; and
   explain Milvus as an open-source vector database for storing, indexing, and
   searching embeddings over unstructured data, then introduce Vector Lakebase
   as the next lake-native expansion around that serving path.
   Assign James sources only to R3. In each weekly pack, create exactly three
   James posts and use `r3_article_summary_share` for exactly one of them. This
   mode follows the approved Feishu exemplar: identify James briefly, summarize
   the full article throughline in connected technical paragraphs, introduce the
   full write-up naturally, put `source_url` on its own line, and close with a
   short invitation for feedback. Use the configured spintax sentence templates
   as variation aids, filling every placeholder from source facts; do not emit
   braces, alternatives, or placeholders in the final draft.
   For `r3_coherent_chapter_rewrite`, select one
   chapter-level argument, record it in `source_chapter`, set `partn` to the
   source-local sequence (`part1`, `part2`, and so on until the source is fully
   covered), preserve its reasoning
   and qualifications, and add only enough context for a standalone post; do
   not summarize the whole article or paste an isolated raw excerpt. Start with
   James's identity, bridge naturally into the next uncovered consecutive source
   section, and continue with later `partn` values until the whole article has
   been covered. This mode does not place a URL in the Reddit body. Set exactly
   one configured `author_rewrite_mode`. Do not run the anonymous title, first-sentence `I`,
   language Buffer, R2 question-quota, Milvus-placement, competitor, brand, or
   no-link rules on this route.
   For every non-James source, use the normal anonymous account route and all of
   its Guidance checks.
4. Within that compliant frame, apply the selected Subreddit's subrules, choose
   only a valid configured Post Category/Post Type, and use its common native
   structure and writing style.
5. Only then apply the audience-preferred technical angle, topic realization,
   and selected account fingerprint. If that angle conflicts with either higher
   level, choose another compliant angle rather than weakening the higher rule.
6. For `r3_article_summary_share`, set `approved_link` to the exact `source_url`
   and place that URL exactly once in its own body paragraph. Use this mode at
   most once per source URL, and never select it when the screened source has
   `generated_count > 0`. Chapter mode and anonymous routes retain their
   configured no-link body policy. For every draft regardless of route, preserve
   `source_url` so delivery writes it to the Feishu `原文` field.
7. For non-James sources, if `r2_short_question_policy` is enabled, produce exactly one R2 short
   question-type post in the pack. Use the configured question Post Type for the
   selected R2 subreddit (`Open Question` for r/AIMemory, `Question | Help` for
   r/LocalLLaMA), set `length_tier` to `short_post`, and keep the question focused
   on Milvus usage, Milvus product features, or a Milvus competitive comparison.
8. Return draft JSON only and hand it to `$reddit-pack-validate`.

If no lower-level choice satisfies all higher levels and the source facts,
reject or replace the source. Never invent experience, customers, benchmarks,
metrics, or results to preserve an angle.

## Output Shape

```json
{
  "source_title": "...",
  "source_url": "https://source.example/...",
  "source_author": "...",
  "pool_record_id": "rec...",
  "items": [
    {
      "account_code": "<configured account>",
      "content_type": "technical_post",
      "subreddit": "<configured subreddit>",
      "post_type": "<configured Post Type>",
      "title": "...",
      "body": "...",
      "disclosure": "<guidance value>",
      "link_policy": "<guidance value>",
      "approved_link": "<exact source_url for James summary mode; empty for chapter mode>",
      "milvus_mention_basis": "<required when current guidance requires it>",
      "angle": "...",
      "voice_fingerprint": "<configured fingerprint>",
      "length_tier": "<configured tier>",
      "author_rewrite_mode": "<required for a configured disclosed-author route>",
      "source_chapter": "<required only for r3_coherent_chapter_rewrite>",
      "partn": "<part1, part2, ...; required only for r3_coherent_chapter_rewrite>"
    }
  ]
}
```

Return only final structured fields and draft content. Never return reasoning,
credentials, private account information, or turn source-author identity into
invented personal history. The James Luan identity opening does not authorize
unsupported biography or experience.
