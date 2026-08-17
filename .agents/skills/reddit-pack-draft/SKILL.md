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
3. Apply Guidance first: resolve Disclosure, then first-person `I` framing and a
   grammatical language Buffer, plus all global anonymity, brand, link, title,
   opening, closing, length, and safety requirements.
4. Within that compliant frame, apply the selected Subreddit's subrules, choose
   only a valid configured Post Category/Post Type, and use its common native
   structure and writing style.
5. Only then apply the audience-preferred technical angle, topic realization,
   and selected account fingerprint. If that angle conflicts with either higher
   level, choose another compliant angle rather than weakening the higher rule.
6. If `r2_short_question_policy` is enabled, produce exactly one R2 short
   question-type post in the pack. Use the configured question Post Type for the
   selected R2 subreddit (`Open Question` for r/AIMemory, `Question | Help` for
   r/LocalLLaMA), set `length_tier` to `short_post`, and keep the question focused
   on Milvus usage, Milvus product features, or a Milvus competitive comparison.
7. Return draft JSON only and hand it to `$reddit-pack-validate`.

If no lower-level choice satisfies all higher levels and the source facts,
reject or replace the source. Never invent experience, customers, benchmarks,
metrics, or results to preserve an angle.

## Output Shape

```json
{
  "source_title": "...",
  "source_url": "https://source.example/...",
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
      "milvus_mention_basis": "<required when current guidance requires it>",
      "angle": "...",
      "voice_fingerprint": "<configured fingerprint>",
      "length_tier": "<configured tier>"
    }
  ]
}
```

Return only final structured fields and draft content. Never return reasoning,
credentials, private account information, or source-author identity as the
anonymous account's personal history.
