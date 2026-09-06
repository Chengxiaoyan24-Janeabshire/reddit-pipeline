# Reddit Browser Monitoring Rubric

## Collection Boundary

- Read only the visible Reddit post page and comments through the selected
  Chrome/Browser session.
- Existing `/r/.../s/...` share URLs may resolve through normal browser
  navigation to a canonical post. Keep the Feishu share URL as `publish_url`
  and record the visibly resolved post URL as `canonical_url`.
- Never open a `.json` URL, inspect network response bodies, call Reddit APIs,
  or read cookies, local storage, profiles, passwords, or session files.
- Never vote, comment, reply, post, follow, message, report, or change account
  state. Do not click controls near voting, replying, awards, sharing, or account
  actions.
- It is acceptable to scroll and expand clearly read-only `more comments` or
  `more replies` controls. Stop after three expansion/scroll passes add no new
  comment text, or after 100 substantive comments have been reviewed.
- Ignore usernames and avatars. Never save raw comment bodies, usernames, or
  comment links in Feishu or the write-bound snapshot.
- Use a `Top 1% Commenter` weight only when that badge is visibly attached to
  the reviewed comment. Never open a profile or infer commenter popularity.

## Target Windows

- Monitor only rows whose `Publish Date` is today through 14 calendar days ago.
- Process `within_7_days` targets first, ordered newest to oldest.
- Process `days_8_to_14` targets second, ordered newest to oldest.
- Do not open rows with missing/future publish dates by default. Missing dates
  may be included only when the user explicitly requests them with
  `--include-undated`; future dates always remain skipped. Posts older than 14 days
  remain skipped by default and may be opened only when the user explicitly
  requests a historical backcheck using `--include-older`.

## Coverage

Use `Monitored` only when visible post metrics and reviewed-comment scores are
exact and every page-reported comment was reviewed. Use `Partial` when any count
or reviewed-comment score is rounded/hidden, or the reviewed comment sample is
smaller than the visible total. Use `Unavailable` when Chrome cannot access or
reliably read the page.

For `Partial` or `Unavailable`, explain the limitation in `monitor_notes`, for
example: `Upvotes displayed as 1.2K; reviewed 40 of 86 visible comments.`

## Monitoring Outputs

### 1. Upvotes

- Record the visible score only.
- Preserve the raw display in `upvotes_display`.
- Normalize `1.2K` to `1200` and set `upvotes_approximate = true`.
- If Reddit shows `Vote`, hides the score, or the value is unreadable, use null;
  never infer it from ratios or other fields.

### 2. Comments

- Record the visible page comment count.
- Record how many substantive comments were actually reviewed in
  `comments_reviewed`.
- Do not treat collapsed, deleted, removed, or empty placeholders as reviewed
  substantive comments.

### 3. Comment Summary

Write two to four concise Chinese sentences covering recurring technical themes,
the main unresolved question, notable criticism or disagreement, and any product
mention. Do not quote comments, identify authors, reproduce insults, or add facts
not visible in the reviewed comments. Preserve product and competitor names
when they are necessary to explain a detected monitoring signal.

### 4. Weighted Comment Sentiment

For every substantive reviewed comment, save one sanitized input with only:

- `sentiment`: `Positive`, `Neutral`, or `Negative` toward the post, its claims,
  or the discussed approach;
- `score_display`: the visible Reddit net score such as `25 points`, `-12`, or
  `Score hidden`;
- `score`: the normalized visible net score, never an inferred upvote/downvote
  count;
- `top_1_percent_commenter`: `true` only when the visible comment carries that
  badge.

The number of sanitized inputs must equal `comments_reviewed`. Do not include
comment text, usernames, profile links, comment links, avatars, or author IDs.

The preview script applies this deterministic formula:

1. Stance baseline: positive `+1`, neutral `0`, negative `-1`.
2. Visible-score bonus by absolute score: `<2` or hidden `0`; `2–4` `0.25`;
   `5–9` `0.5`; `10–24` `1.0`; `25–99` `1.5`; `100+` `2.0`.
3. A positive visible score applies the bonus in the comment stance direction.
   A negative visible score reverses the bonus because the community visibly
   rejected that stance. Thus a highly upvoted positive comment strengthens the
   positive result, while a heavily downvoted negative comment offsets or can
   reverse its negative contribution. This never estimates exact downvotes.
4. A visible `Top 1% Commenter` badge adds `0.5` in that comment's own stance
   direction. This component remains separate from the community score, so a
   prominent negative commenter and community rejection can counterbalance.
5. Normalize total contribution by total possible weight. Classify `>= 0.15` as
   `Positive`, `<= -0.15` as `Negative`, and the interval between them as
   `Mixed`. If all reviewed comments are neutral, use `Neutral`; if no comments
   were reviewed, use `None`.

`Negative Signal` remains `Yes` when meaningful criticism appears even if the
weighted overall sentiment is `Positive` because the criticism was strongly
downvoted. The summary should explain that shape without quoting anyone.

### 5. Question Signal

- `None`: no material question directed at the post or author.
- `Yes`: at least one substantive question asks for clarification, evidence,
  implementation detail, comparison, source, or correction that may warrant
  human review or a response.

This field recommends review only. The Skill never writes a Reddit reply.

### 6. Negative Signal

- `None`: no meaningful negative signal.
- `Yes`: criticism, dissatisfaction, skepticism, a negative product claim,
  insults, harassment, spam/deception accusations, or severe hostility appears.

Summarize the issue neutrally; do not copy abusive language.

### 7. Debate Signal

- `None`: comments broadly agree or contain unrelated one-off opinions.
- `Yes`: at least two materially different positions appear, or sustained
  opposing positions develop across comments or branches.

Do not mark normal clarification or one dissenting comment as polarized.

### 8. Product Signal

- `None`: reviewed comments do not mention Milvus.
- `Yes`: at least one reviewed comment explicitly mentions Milvus.

This signal is based on comments, not the published post body. Do not infer a
mention from the source Blog, title, or account metadata.

### 9. Competitor Signal and Mentions

- `None`: reviewed comments do not mention or clearly reference another
  database, vector database, retrieval product, or directly competing data
  infrastructure.
- `Yes`: at least one reviewed comment names or clearly references an
  alternative database or competing product.

Store normalized names in `competitor_mentions`, separated by commas, for
example `Pinecone, Qdrant, Weaviate`. Exclude Milvus from this field because it
belongs to `product_signal`. For an unambiguous generic reference without a
name, use `Other database (unnamed)`. Do not infer a competitor from the post
body or source Blog.

### 10. Impression (7 days)

Keep only the Feishu `Impression (7 days)` number field because it is populated
from a separate account analytics surface. Do not read it from the public Reddit
page, estimate it, clear it, or include it in the browser write patch.

## Observation Shape

Use the following internal structure when handing browser observations to the
deterministic preview script. This is not Reddit JSON and is never copied from a
Reddit endpoint.

```json
{
  "observations": [
    {
      "record_id": "rec...",
      "draft_id": "RD-...",
      "publish_url": "https://www.reddit.com/r/.../comments/.../",
      "canonical_url": "https://www.reddit.com/r/.../comments/.../",
      "page_title": "Visible page title",
      "observed_at": "2026-08-07T10:00:00+00:00",
      "upvotes_display": "120",
      "upvotes": 120,
      "upvotes_approximate": false,
      "comments_display": "2",
      "comments": 2,
      "comments_approximate": false,
      "comments_reviewed": 2,
      "comment_sentiments": [
        {
          "sentiment": "Positive",
          "score_display": "25 points",
          "score": 25,
          "score_approximate": false,
          "top_1_percent_commenter": true
        },
        {
          "sentiment": "Negative",
          "score_display": "-12 points",
          "score": -12,
          "score_approximate": false,
          "top_1_percent_commenter": false
        }
      ],
      "comment_summary": "评论主要讨论……",
      "question_signal": "Yes",
      "negative_signal": "Yes",
      "debate_signal": "Yes",
      "product_signal": "Yes",
      "competitor_signal": "Yes",
      "competitor_mentions": "Pinecone, Qdrant",
      "monitor_status": "Monitored",
      "monitor_notes": "Reviewed all 2 visible comments."
    }
  ]
}
```
