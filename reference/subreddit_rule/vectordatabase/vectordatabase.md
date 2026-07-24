# r/vectordatabase — current drafting guidance

## Scope

Use this community for vector database architecture, cost, migration, indexing,
filtering, benchmarks, self-hosting, scaling, consistency, and production
operations.

## Post Type

The weekly pipeline uses `No fixed post type`. This value records that the
community rules were checked; it is not a flair to imitate.

## Native structure

1. State the system decision or failure clearly.
2. Give the workload shape where supported: vector count, dimensions, QPS,
   latency target, filtering, update rate, hardware, consistency, and budget.
3. Explain the benchmark or comparison method, including limitations.
4. Name operational costs such as compaction, index rebuilds, memory, storage,
   migrations, backups, and observability.
5. Keep a focused question about the tradeoff when it fits naturally; a question
   ending is optional.

## Identity and brand boundary

- R2 is anonymous and `disclosure` stays empty.
- `I built` is allowed only when source-supported.
- Do not reveal identity, employer, contributor/maintainer role, affiliation,
  customer identity, or project representation.
- The title must not mention Milvus. The body may mention Milvus once only when
  the technical background or data is source-supported. Never mention Zilliz.
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
