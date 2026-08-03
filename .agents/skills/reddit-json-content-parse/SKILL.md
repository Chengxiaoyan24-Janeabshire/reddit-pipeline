---
name: reddit-json-content-parse
description: Parse complete Reddit submission JSON pasted into the Feishu Reddit Persona Pipeline field `Reddit JSON Content`, then preview or write vote metrics, estimated downvotes, post status, a comment summary, public-opinion alerts, and Milvus-related signals. Use when the user has manually copied Reddit `.json` content into Feishu and wants it analyzed without any Reddit network request. Never generate JSON URLs or perform Reddit account activity.
---

# Reddit JSON Content Parse

Run commands from the project root. This workflow reads only the complete JSON
text already stored in Feishu `Reddit JSON Content`; it never opens or requests
Reddit.

## Workflow

1. Preview every `Status = Published` row. Rows with empty JSON content are
   reported under `waiting_for_content` and are not failures. Save the exact
   reviewed result as a write-bound snapshot:

```bash
python3 scripts/parse_reddit_json_content.py \
  --from-feishu \
  --sample-comments 12 \
  --snapshot-out packs/reddit-json-content-preview.json
```

2. Review each report. The automatic summary is aggregate-only and Feishu never
   receives raw comment text or Reddit usernames. Sanitized samples appear only
   in the local dry-run when `--sample-comments` is nonzero.

If the summary, alert, or signal needs editorial correction, create an analysis
JSON keyed by `record_id`, `draft_id`, or `publish_url`:

```json
{
  "recv_example": {
    "comment_summary": "评论主要讨论检索质量、部署成本和多跳查询的取舍。",
    "public_opinion_alert": "Watch",
    "milvus_signal": ["Milvus Mention", "Milvus Comparison"]
  }
}
```

Then create a new snapshot from the reviewed result:

```bash
python3 scripts/parse_reddit_json_content.py \
  --from-feishu \
  --analysis-json packs/reddit-json-analysis.json \
  --snapshot-out packs/reddit-json-content-preview.json
```

3. Add `--write` only after the user explicitly approves the exact preview.
The write command rereads Feishu, verifies the target rows and SHA-256 of every
`Reddit JSON Content` value, and refuses to write if content or schema changed:

```bash
python3 scripts/parse_reddit_json_content.py \
  --from-feishu \
  --snapshot-in packs/reddit-json-content-preview.json \
  --ensure-fields \
  --write
```

## Feishu Contract

Read `Reddit JSON Content`. Never overwrite either `Reddit JSON` or
`Reddit JSON Content`.

Write only:

- `Upvotes`, `Comments`, `Downvotes (Estimated)`, and `Upvote Ratio`;
- `Reddit Post Status`, `Comment Summary`, `Public Opinion Alert`,
  `Milvus Signal`, and `Reddit Metrics Updated At`;
- existing `Status = Cancel` only when valid pasted JSON proves the post is
  `Removed` or `Deleted`.

Reddit does not expose exact public downvotes. Keep the field name
`Downvotes (Estimated)` and treat the derived value as approximate.

Any detected negative comment produces at least `Watch`; stronger or repeated
negative discussion may produce `Alert`. Clear `Milvus Signal` when no pasted
comment mentions Milvus or Zilliz.

## Report

Report target count, parsed rows, rows waiting for content, invalid JSON errors,
field-plan changes, records written, removed/deleted posts, alert rows, Milvus
signal rows, and the downvote-estimate limitation. Preserve the preview snapshot
when a live write fails and report any partial writes explicitly.
