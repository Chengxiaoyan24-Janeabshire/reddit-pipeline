# Reddit 内容建议及范例

## 写作原则

1. 先写具体问题，再写背景。
2. 给出规模、延迟、成本、更新频率、过滤条件或运维限制。
3. 明确区分已观察到的结果、来源支持的事实和仍待验证的判断。
4. 写出失败条件与取舍，不把单次测试包装成普遍结论。
5. 开放问题自然存在时保留；不为了格式强行增加。

真实的短 Discussion 或 Resource Request 使用 `short_post`；普通技术帖使用
`standard_post`。短帖不需要为了达到 standard 长度而填充，但仍要有足够背景。

R1/R2 保持匿名，Disclosure 为空。`I built` 可以使用，但必须有来源支持，且
不得附带身份、雇主、贡献者/维护者角色或 affiliation。标题不得出现 Milvus；
正文最多可出现一次 Milvus，并填写 `milvus_mention_basis`。

R1 和 R2 都不带链接。标题、正文和任何链接字段都不得出现 URL。

## 范例 1：RAG Discussion

### Title

When does one-hop expansion stop being enough for multi-hop retrieval?

### Body

I built a retrieval flow that starts with semantic search, expands one hop through
stored entity relationships, reranks the candidates, and then calls the generator.
The fixed query path is easier to debug than an agent that decides repeatedly
whether to retrieve again.

The weak point is relationship maintenance. Entity deduplication, updates, and
high-degree nodes can become more expensive than the query itself. The design
still feels reasonable for bounded two-to-four-hop questions, but I am less
confident when relationships change frequently or users need exploratory graph
queries.

For teams that have tried a similar design, what was the point where a dedicated
graph layer became simpler than maintaining references inside the retrieval store?

## 范例 2：AI Agents Discussion

### Title

What belongs in an agent harness instead of the prompt?

### Body

Long-running agent failures often look less like prompt failures and more like
environment failures: stale documentation, weak validation, missing runtime
evidence, or no clear stopping condition.

My current approach is to keep the top-level instructions small, move enforceable
rules into tests and linters, and give the agent direct access to logs and browser
state. A separate evaluator can help with subjective quality, but it also adds
cost and another component that can be wrong.

For longer agent tasks, which improvement changed reliability most in practice:
better documentation, stronger runtime checks, richer tools, or a separate evaluator?

## 范例 3：Vector Database Operations

### Title

Should segment count be a first-class production metric?

### Body

A compaction test made me rethink how much query cost can come from index fan-out.
Merging several sealed segments into one reduced the number of indexes searched per
query and improved latency, but the merge also required index rebuild work, memory,
and I/O.

That makes aggressive compaction a poor default for collections with steady writes
and deletes. A more useful policy may combine segment count, size distribution,
time since the last meaningful write, and observed query latency.

Do teams usually trigger compaction from thresholds, schedule it for quiet windows,
or require manual approval after checking current write load?

## 范例 4：Data Engineering Discussion

### Title

Where should incremental embedding sync own its checkpoints?

### Body

An incremental pipeline has at least three different progress markers: the source
change stream position, the transformation version, and the destination write
checkpoint. Treating them as one offset makes replay simple until the embedding
model changes or a partial batch succeeds.

I am leaning toward immutable source offsets plus versioned transformation metadata,
with destination idempotency handled separately. The tradeoff is more state to
observe and more complicated recovery tooling.

How do you separate these checkpoints without making routine backfills and partial
replays too operationally expensive?

## 使用提醒

这些范例只展示结构和语气，不能直接当作已验证事实发布。实际草稿必须以来源
为依据，并通过账号、Subreddit、Post Type、匿名、链接和内容校验。
