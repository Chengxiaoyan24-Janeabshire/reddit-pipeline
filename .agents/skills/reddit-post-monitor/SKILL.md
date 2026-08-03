---
name: reddit-post-monitor
description: Read published Reddit post URLs through their public .json endpoints, collect vote/comment metrics and post status, summarize comments, detect negative-public-opinion alerts and Milvus-related signals, and preview or write the results to the Feishu Reddit Persona Pipeline. Use for monitoring published Reddit posts, refreshing engagement fields, checking whether posts were removed or deleted, or reviewing comment sentiment and product signals. Never publish or interact on Reddit.
---

# Reddit Post Monitor

Run commands from the project root. Use only public read-only Reddit JSON GETs;
never log in, post, comment, reply, vote, or perform account activity.
Feishu access requires the repository's normal `FEISHU_CONFIG_PATH` or
gitignored `config/feishu-config.json` configuration.

## Workflow

1. Preview the Feishu field plan and all `Status = Published` rows with a
   non-empty `Publish URL`. Save the exact reviewed result as a write-bound
   snapshot:

```bash
python3 scripts/sync_reddit_post_metrics.py \
  --from-feishu \
  --ensure-fields \
  --snapshot-out packs/reddit-monitor-preview.json
```

Reddit `/r/<subreddit>/s/<token>` and `redd.it` links are resolved to canonical
submission URLs before `.json` is appended. Only HTTPS Reddit submission URLs
are accepted.

If Reddit returns HTTP 403 or 429 to the command-line client, use the reported
`reddit_json_url` in a browser and save the returned JSON under the reported
`saved_json_filename` in `packs/reddit-json/`. Then repeat the preview without
making Reddit requests:

```bash
python3 scripts/sync_reddit_post_metrics.py \
  --from-feishu \
  --ensure-fields \
  --reddit-json-dir packs/reddit-json \
  --snapshot-out packs/reddit-monitor-preview.json
```

2. Review each report's heuristic `comment_summary`, `public_opinion_alert`,
and `milvus_signal`. Reddit author fields are never collected, raw comment text
is never written to Feishu, and the default report does not emit comment
samples. For local human review only, add `--sample-comments 12`; those samples
remain outside Feishu. If judgment needs correction, provide an analysis JSON
keyed by `record_id`, `publish_url`, or `reddit_json_url`:

```json
{
  "rec_example": {
    "comment_summary": "评论主要比较检索质量和运维成本，其中一条高赞讨论报告了可复现的过滤问题。",
    "public_opinion_alert": "Watch",
    "milvus_signal": ["Milvus Mention", "Milvus Comparison"]
  }
}
```

Re-preview with:

```bash
python3 scripts/sync_reddit_post_metrics.py \
  --from-feishu \
  --ensure-fields \
  --analysis-json analysis.json \
  --snapshot-out packs/reddit-monitor-preview.json
```

3. Add `--write` only after the user explicitly authorizes the exact snapshot,
missing field plan, and record set. The write command does not refetch Reddit;
it verifies the snapshot digest and blocks if the Feishu targets or field plan
changed after preview:

```bash
python3 scripts/sync_reddit_post_metrics.py \
  --from-feishu \
  --ensure-fields \
  --snapshot-in packs/reddit-monitor-preview.json \
  --write
```

## Local URL Input

For read-only testing without Feishu, pass a JSON list of Reddit URLs or objects
with `publish_url` and optional `record_id`:

```bash
python3 scripts/sync_reddit_post_metrics.py --input-json reddit-posts.json
```

The script strips tracking query parameters, appends `.json`, and requests the
submission plus top-sorted comments. Do not treat the endpoint as permission for
Reddit account activity. Local input is read-only and can never be combined with
`--write`.

## Feishu Contract

Maintain these fields in `Reddit Persona Pipeline`:

- `Reddit JSON URL`, `Upvotes`, `Comments`, `Downvotes (Estimated)`, and
  `Upvote Ratio`;
- `Reddit Post Status`, `Comment Summary`, `Public Opinion Alert`,
  `Milvus Signal`, and `Reddit Metrics Updated At`.

Reddit does not expose an exact public downvote count. The estimate uses
`score + upvote_ratio`, remains approximate, and must never be presented as an
exact metric.

Set the existing `Status` to `Cancel` only when a successful JSON response shows
the post is `Removed` or `Deleted`. `Locked`, `Archived`, `Unavailable`, fetch
errors, deleted authors, and rate limits do not automatically cancel a row.

`Public Opinion Alert` is a review triage signal, not a definitive sentiment
label. `Milvus Signal` comes from comments, may include positive, negative,
question, comparison, or adoption intent, and must be cleared when no qualifying
comment remains.

## Report

Report target count, fetched/failed URLs, missing fields, records written,
removed/deleted posts, alert rows, Milvus signal rows, and the downvote-estimate
limitation. A 403/429 report must include the canonical JSON URL and saved-file
recovery name. Preserve the snapshot and dry-run evidence when any live update
fails; partial field or record writes must be reported explicitly.
