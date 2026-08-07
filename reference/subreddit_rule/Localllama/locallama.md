# r/LocalLLaMA — current drafting guidance

## Scope

Use this community for local and open-weight language models, self-hosted
inference, quantization and hardware fit, local RAG, model evaluation, and
practical runtimes or tools.

## Post Types

- `Discussion`: a focused tradeoff or design discussion about local models,
  inference, quantization, RAG, evaluation, or operating constraints.
- `Question | Help`: a concrete troubleshooting or selection question with the
  relevant model, runtime, hardware, data, and observed failure context.
- `Resources`: a source-supported set of tools, models, methods, or references
  that remains useful without an outbound link.

## Stable persona versus screenshot overlay

R2 keeps the same production-minded account fingerprint in every Post Type.
Screenshots may influence the local structure, but must not transfer:

- usernames, personal circumstances, or identity claims;
- tool endorsements, links, prices, subscription claims, or list-size metrics;
- unsupported model, hardware, quality, latency, or throughput results;
- wording, typos, or claims from the example author.

## Native structure

1. Write the title from a first-person singular perspective or as an explicit
   question ending in `?`; never use a fully third-person declarative title.
2. Use the first sentence to establish a source-supported first-person
   perspective and state the local-model, inference, or RAG problem directly.
3. Include at least one grammatical language buffer such as `probably`, `one
   concern I have`, `my current view`, or `I would likely` for a judgment or
   uncertainty; keep source facts and measurements direct.
4. Include source-supported constraints such as model size, quantization,
   context length, RAM/VRAM, CPU/GPU, retrieval corpus, latency, or privacy.
5. Explain what was tried or compared and separate observations from
   assumptions.
6. For `Question | Help`, make the failure and requested decision specific.
7. For `Resources`, organize the categories or selection criteria so the post
   is complete without a link.
8. For `Discussion`, state the unresolved choice and invite replies softly,
   such as `Would love to hear your thoughts.`, rather than ending with a hard
   question. Keep `Question | Help` specific enough to answer.

## Identity, brand, and links

- R2 is anonymous and `disclosure` stays empty.
- `I built` is allowed only when source-supported.
- Do not reveal identity, employer, contributor/maintainer role, affiliation,
  customer identity, or project representation.
- The title must not mention Milvus. Every body must mention Milvus exactly once
  using source-supported technical background or data and must include a
  `milvus_mention_basis`. Phrase the mention indirectly as a category example or
  peer, such as `vector databases like Milvus`; never use direct product
  placement. Never mention Zilliz.
- Always use `no_link`; do not include URLs.

## Avoid

- copied tool lists, product endorsements, personal details, links, or metrics;
- invented first-person local setup or hardware experience;
- universal conclusions from one model, quantization, workload, or benchmark;
- turning `Resources` into link bait or changing the R2 persona to imitate a
  screenshot author.
