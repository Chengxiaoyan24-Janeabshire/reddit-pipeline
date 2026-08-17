# Reddit References

References contain the selected account, Subreddit, and audience context used
inside the boundaries established by Guidance. They do not define how the
workflow runs and cannot redefine global editorial pass/fail policy.

- `accounts/`: R1/R2 persona, topic routing, and stable voice fingerprints.
- `slots/`: machine JSON and generated MD review for the four subreddit
  overlays, Post Types, native structure, and sanitized screenshot pointers.
- `topic_bank.json`: shared advisory topic taxonomy used during screening.
- `accounts/RULES.md`, `TOPIC_RULES.md`, and `slots/RULES.md`: generated
  human-readable reviews of the machine JSON.

Workflow and global editorial rules live in `guidance/reddit/`. Images and
generated PDFs live in `resource/reddit/`.

Within editorial work, Reference content has two different precedence levels:

1. the selected `slots/` Subreddit reference applies its subrules, valid Post
   Category/Post Type, native structure, and common style after global Guidance;
2. `accounts/` and `topic_bank.json` then provide the audience-preferred angle,
   topic fit, and voice fingerprint.

The audience layer cannot override either Guidance or the selected Subreddit.
If its preferred vector-database, retrieval, memory, or local-inference angle
does not fit both higher levels and the source facts, choose another angle or
reject the source.

JSON remains the bottom runtime contract. The generated Markdown files are the
top review layer for human inspection. Update JSON through the AI, then run
`python3 scripts/render_rule_docs.py`; never maintain the two layers by hand.
