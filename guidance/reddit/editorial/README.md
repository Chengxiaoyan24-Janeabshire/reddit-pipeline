# Editorial Guidance

These machine-readable files define the first and highest editorial instruction
level for every account and Subreddit slot.

- `editorial_policy.json`: disclosure, anonymity, first-person framing,
  language Buffer, title, brand, link, opening, closing, and safety policy.
- `content_length_rules.json`: short, standard, long, and code-long tiers.
- `RULES.md`: generated human-readable review of both JSON files.

AI and runtime validation read the JSON. Humans inspect `RULES.md`. Change the
JSON through the AI, then run `python3 scripts/render_rule_docs.py`; do not edit
the generated review independently.

After this Guidance passes, the selected Subreddit reference applies its
subrules, valid Category/Post Type, native structure, and style. Account and
audience references are third and may shape only the remaining compliant
choices.
