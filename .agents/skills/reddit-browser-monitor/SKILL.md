---
name: reddit-browser-monitor
description: Monitor Reddit posts published within the last 14 days through the user-selected Chrome or in-app Browser session, prioritizing posts within 7 days, then preview or write visible metrics, weighted comment sentiment, comment summaries, and review signals to Feishu while preserving the separately populated Impression (7 days) field. Use for "$reddit-browser-monitor", "检查已发布 Reddit 帖子", "自动监测 Reddit 评论", or replacing the retired pasted Reddit JSON workflow. Read visible page state only; never use Reddit JSON/API responses or perform Reddit account activity.
---

# Reddit Browser Monitor

Use the Browser control skill for every Reddit page action. If the user selects
Chrome, keep that browser choice for the run. If Chrome is disconnected or
authentication blocks the page, ask the user to connect or sign in there; do not
switch browsers or bypass the block without approval.

Read [references/signal-rubric.md](references/signal-rubric.md) before analyzing
comments.

## Workflow

1. List Feishu rows with `Status = Published`, a valid Reddit `Publish URL`, and
a usable `Publish Date`. The command returns posts from the last 7 days first,
then posts 8–14 days old. Missing/future dates and posts older than 14 days are
reported as skipped and must not be opened for monitoring:

```bash
python3 scripts/reddit_browser_monitor.py --list-targets
```

2. Open each target URL in the returned order. Read visible page state only.
Do not use `.json` URLs, Reddit APIs, browser network-response inspection, raw
page source dumps, cookies, or session storage. For an existing Reddit `/s/`
share URL, follow the normal visible navigation redirect and record the resolved
canonical post URL; never construct or guess a replacement URL.

3. Collect visible upvotes, visible comment count, comment summary, question
signal, negative signal, debate signal, Milvus product signal, competitor
signal, and normalized competitor mentions. For every substantive reviewed
comment, record only its `Positive` / `Neutral` / `Negative` stance, visible net
comment score, and whether the comment visibly carries Reddit's `Top 1%
Commenter` badge. The deterministic preview script computes `Comment Sentiment`;
do not count positive comments alone or manually override the weighted result.
Record comment coverage and rounded/hidden score limitations. Preserve product
and competitor names when they are material to the monitoring result, but never
persist usernames, raw comments, comment links, or abusive quotes.

`Impression (7 days)` is the only retained impression field and is populated
from separate account analytics. Browser monitoring may ensure the field exists
but must never write, clear, or estimate its value.

Use only `Yes` or `None` for question, negative, debate, product, and competitor
signals. Put severity, disagreement shape, product names, and response context in
the aggregate summary, monitoring notes, or `Competitor Mentions`. `Comment
Sentiment` separately uses `None`, `Positive`, `Mixed`, `Neutral`, or `Negative`.

4. Save the structured browser observations to an ignored local file, then
validate and create the exact write-bound preview snapshot:

```bash
python3 scripts/reddit_browser_monitor.py \
  --observations-file packs/reddit-browser-observations.json \
  --snapshot-out packs/reddit-browser-monitor-preview.json
```

5. Report every observation and limitation. Stop after preview unless the user
explicitly approves that exact snapshot for Feishu write.

6. After approval, write only the reviewed snapshot:

```bash
python3 scripts/reddit_browser_monitor.py \
  --snapshot-in packs/reddit-browser-monitor-preview.json \
  --ensure-fields \
  --write
```

The write command rereads Feishu and fails closed if target rows, Publish URLs,
or the field plan changed after preview.

## Safety Boundary

- Browser actions are read-only: navigation, scrolling, accessibility snapshots,
  and clearly read-only comment expansion only.
- Never vote, post, comment, reply, message, follow, report, or alter Reddit
  account state.
- Never estimate hidden upvotes or claim that rounded values are exact.
- Treat a visible comment score as Reddit's displayed net score, never as exact
  upvote or downvote counts. Use a Top 1% weight only when the badge is visibly
  attached to that comment; never inspect profiles or infer commenter rank.
- Never update Feishu without explicit approval of the exact preview snapshot.
- Do not delete the retired live Feishu JSON fields automatically. They may be
  cleaned up only after a separate explicit schema-cleanup request.

## Report

Report the within-7-day and 8–14-day target counts, successfully monitored rows,
partial/unavailable rows, comments reviewed versus visible totals, weighted
comment-sentiment counts, Top 1% weighted comment count, question/negative/
debate/product/competitor signal counts, preview snapshot path, and any records
written. State explicitly that posts older than 14 days were skipped, the run
used visible browser state rather than Reddit JSON or API data, and `Impression
(7 days)` was left untouched.
