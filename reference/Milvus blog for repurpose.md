# Sanitized Reddit adaptation examples

The original catalog pages are retained as source inventory. The old Reddit
examples have been replaced by the current drafting boundary below.

## Adaptation boundary

- R1/R2 remain anonymous and use an empty Disclosure.
- `I built` is allowed only when source-supported and without identity, employer,
  contributor/maintainer role, affiliation, customer identity, or project
  representation.
- Do not mention Milvus in the title. The body may mention Milvus once when the
  technical background or data is source-supported; record the basis in
  `milvus_mention_basis`. Never mention Zilliz.
- R1 and R2 never include outbound links.
- Keep the adaptation focused on the engineering problem, constraints, and open
  questions.
- Do not repeat benchmark numbers without the full setup and limitations.

## Example: substring-filter bottleneck

### Title

How would you index substring filters without making writes too expensive?

### Body

Vector search can be fast while keyword or substring filters quietly dominate the
query path. A scan-based `LIKE '%...%'` condition is simple, but it becomes hard to
justify once the dataset and concurrent query count grow.

An n-gram inverted index can narrow the candidate set before evaluating the full
pattern. The tradeoff is index size, write amplification, and sensitivity to the
chosen n-gram range. It also does not remove the need to validate the final match.

For workloads that mix semantic search with exact error strings or function names,
how do you decide between n-grams, a separate text index, or a different storage
layout?

## Example: GPU build and CPU serving

### Title

Does separating GPU index construction from CPU query serving hold up operationally?

### Body

Graph-style ANN indexes can be expensive to build, while keeping GPUs online for
bursty query serving can be difficult to justify. One design is to use GPU
parallelism during construction, persist the resulting graph in a CPU-friendly
format, and serve queries from CPU replicas.

The architecture shifts cost toward build time, but it introduces compatibility,
artifact distribution, rebuild, and rollback questions. It may also behave
differently when updates are frequent rather than batch-oriented.

For teams that split index build and query serving this way, which operational issue
became the real bottleneck: artifact movement, update freshness, CPU memory, or
cross-version compatibility?
