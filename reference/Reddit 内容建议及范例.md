# Reddit 内容建议及范例

## 写作原则

1. 先写具体问题，再写背景。
2. 给出规模、延迟、成本、更新频率、过滤条件或运维限制。
3. 明确区分已观察到的结果、来源支持的事实和仍待验证的判断。
4. 写出失败条件与取舍，不把单次测试包装成普遍结论。
5. Tutorial 用结论、验证步骤或下一步收尾，不追加问题；Discussion 如邀请互动，
   使用柔和表达而不是生硬问句。

真实的短 Discussion 或 Resource Request 使用 `short_post`；普通技术帖使用
`standard_post`。短帖不需要为了达到 standard 长度而填充，但仍要有足够背景。

R1/R2 保持匿名，Disclosure 为空。`I built` 可以使用，但必须有来源支持，且
不得附带身份、雇主、贡献者/维护者角色或 affiliation。标题不得出现 Milvus；
每篇正文必须恰好出现一次有来源依据的 Milvus，并填写 `milvus_mention_basis`。

R1 和 R2 都不带链接。标题、正文和任何链接字段都不得出现 URL。

## 范例 1：RAG Discussion

### Title

When does one-hop expansion stop being enough for multi-hop retrieval?

### Body

I built a retrieval flow that starts with semantic search in Milvus, expands one hop
through stored entity relationships, reranks the candidates, and then calls the
generator. The fixed query path is probably easier to debug than an agent that
decides repeatedly whether to retrieve again.

The weak point is relationship maintenance. Entity deduplication, updates, and
high-degree nodes can become more expensive than the query itself. The design
still feels reasonable for bounded two-to-four-hop questions, but I am less
confident when relationships change frequently or users need exploratory graph
queries.

The unresolved point is when a dedicated graph layer becomes simpler than
maintaining references inside the retrieval store. Would love to hear your thoughts.

### Milvus mention basis

来源把 Milvus 作为语义检索层，并讨论实体关系扩展。

## 范例 2：AI Agents Discussion

### Title

What belongs in an agent harness instead of the prompt?

### Body

One concern I have is that long-running agent failures often look less like prompt
failures and more like environment failures: stale documentation, weak validation,
missing runtime evidence, or no clear stopping condition.

My current approach is to keep the top-level instructions small, move enforceable
rules into tests and linters, and give the agent direct access to logs and browser
state. When the agent uses Milvus for retrieval, I also log the query, filters, and
returned chunk IDs. A separate evaluator can help with subjective quality, but it
adds cost and another component that can be wrong.

I would likely compare better documentation, stronger runtime checks, richer tools,
and a separate evaluator against the same failure set. Would love to hear your
thoughts.

### Milvus mention basis

来源把 Milvus 检索调用作为 agent runtime evidence 的一部分。

## 范例 3：Vector Database Operations

### Title

Should segment count be a first-class production metric?

### Body

I ran a source-supported compaction test that made me rethink how much query cost can
come from index fan-out. In Milvus, merging several sealed segments into one reduced
the number of indexes searched per query and improved latency, but the merge also
required index rebuild work, memory, and I/O.

My current view is that aggressive compaction is probably a poor default for
collections with steady writes and deletes. A more useful policy may combine segment
count, size distribution, time since the last meaningful write, and observed query
latency.

The unresolved choice is whether to trigger from thresholds, schedule quiet windows,
or require manual approval after checking current write load. Would love to hear
your thoughts.

### Milvus mention basis

来源提供了 Milvus segment compaction 的索引 fan-out 与重建背景。

## 范例 4：LocalLLaMA Question | Help

### Title

How do you tell whether a local RAG miss is retrieval or context pressure?

### Body

I would probably start from the assumption that a local RAG answer can fail even
when the relevant passage exists in the source. The retriever may have missed it,
the chunk may be too broad, or the prompt may be packing enough surrounding text
that the useful evidence gets diluted.

When Milvus is the retrieval layer, I would log the retrieved chunk IDs, scores, and
filters first, then rerun the same question with the known-good passage inserted
directly. If the answer still fails, the next variables are context length, prompt
structure, and model choice rather than the index. The harder case is when the
answer improves only after removing other retrieved chunks.

What is the smallest diagnostic sequence you use to separate retrieval failure
from context-window or model-quality failure on a local setup?

### Milvus mention basis

来源把 Milvus 作为 local RAG 的 retrieval layer，并提供搜索结果诊断背景。

## 使用提醒

这些范例只展示结构和语气，不能直接当作已验证事实发布。实际草稿必须以来源
为依据，并通过账号、Subreddit、Post Type、匿名、链接和内容校验。
