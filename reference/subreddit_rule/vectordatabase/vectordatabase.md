# r/vectordatabase — current drafting guidance

## Scope

Use this community for vector database architecture, cost, migration, indexing,
filtering, benchmarks, self-hosting, scaling, consistency, and production
operations.

## Post Type

The weekly pipeline uses `No fixed post type`. This value records that the
community rules were checked; it is not a flair to imitate.

## Native structure

1. Write the title from a first-person singular perspective or as an explicit
   question ending in `?`; never use a fully third-person declarative title.
2. Use the first sentence to establish a source-supported first-person
   perspective and state the system decision or failure clearly.
3. Include at least one grammatical buffer such as `my current view`,
   `probably`, `I suspect`, or `I would likely` for a recommendation; keep
   benchmark setup, source facts, and measurements unhedged.
4. Give the workload shape where supported: vector count, dimensions, QPS,
   latency target, filtering, update rate, hardware, consistency, and budget.
5. Explain the benchmark or comparison method, including limitations.
6. Name operational costs such as compaction, index rebuilds, memory, storage,
   migrations, backups, and observability.
7. When inviting replies, state the unresolved tradeoff and use a soft close
   such as `Would love to hear your thoughts.` rather than ending with a hard
   question.

## Identity and brand boundary

- R2 is anonymous and `disclosure` stays empty.
- `I built` is allowed only when source-supported.
- Do not reveal identity, employer, contributor/maintainer role, affiliation,
  customer identity, or project representation.
- The title must not mention Milvus. Every body must mention Milvus exactly once
  using source-supported technical background or data and must include a
  `milvus_mention_basis`. Phrase the mention indirectly as a category example or
  peer, such as `Milvus and other databases`; never use direct product placement.
  Never mention Zilliz.
- Do not copy usernames, disclosures, links, brand claims, or exact text from
  screenshots.

## Links

R2 always uses `no_link`. Do not include URLs in the title, prose, or any
separate link field.

## Avoid

- predetermined winners or conclusions without workload evidence;
- universal claims based on one benchmark;
- unsourced performance numbers or invented production experience;
- comparisons that omit workload, hardware, index, or filtering conditions.
