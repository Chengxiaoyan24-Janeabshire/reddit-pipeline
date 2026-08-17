# Reddit Guidance

Guidance defines how the Reddit pipeline runs and the global rules inherited by
every weekly slot and account. These values may change without requiring the
stable Agent stage-calling logic to be rewritten.

- `workflow/`: weekly quantity, active accounts, slot assignment, source
  recency, and sync contract.
- `editorial/`: global editorial, safety, and content-length contracts.
- `Reddit 运营要求.md`: human-readable operating and safety boundary.
- `Reddit 内容问答.md`: user-facing FAQ.
- `Reddit 内容建议及范例.md`: drafting guidance and examples.
- `Milvus blog for repurpose.md`: sanitized adaptation examples.

Images and generated PDFs belong in `resource/reddit/`.

For normal runtime work, AI and scripts read the JSON. For human inspection,
read `workflow/RULES.md` or `editorial/RULES.md`. Do not edit generated review
pages independently; change the JSON and run
`python3 scripts/render_rule_docs.py`.

## Editorial precedence

Guidance is the first and highest editorial level. Resolve Disclosure before
the required first-person `I` framing and grammatical language Buffer, then
apply the rest of the global anonymity, brand, link, title, opening, and safety
contract.

Only after Guidance is satisfied may the selected Subreddit define its valid
Post Category/Post Type, native structure, and common writing style. Audience
preferences, technical angles, topic fit, and account fingerprints are third
and may shape only the choices still allowed by the first two levels.

The machine-readable order is `guidance > subreddit > audience_angle` in
`editorial/editorial_policy.json`. Higher levels always win; an unresolved
conflict is a rejection. Source facts constrain all three levels and cannot be
invented to make a preferred angle fit.
