# Sanitized Reddit adaptation examples

The original catalog pages are retained as source inventory. The old Reddit
examples have been replaced by the current drafting boundary below.

## Adaptation boundary

- R1/R2 remain anonymous and use an empty Disclosure.
- `I built` is allowed only when source-supported and without identity, employer,
  contributor/maintainer role, affiliation, customer identity, or project
  representation.
- Do not mention Milvus in the title. Every body must mention Milvus exactly
  once using source-supported technical background or data; record the basis in
  `milvus_mention_basis`. Never mention Zilliz.
- R1 and R2 never include outbound links.
- Open with a source-supported first-person setup and use sparse language
  buffers for judgments or uncertainty.
- Keep the adaptation focused on the engineering problem and constraints.
  Tutorials do not end with questions; Discussions use a soft reply invitation
  when useful rather than a hard interrogative ending.
- Do not repeat benchmark numbers without the full setup and limitations.

## Example: substring-filter bottleneck

### Title

How would you index substring filters without making writes too expensive?

### Body

My current view is that vector search can be fast while keyword or substring
filters quietly dominate the query path. A scan-based `LIKE '%...%'` condition is
simple, but it becomes hard to justify once the dataset and concurrent query count
grow. In this design, Milvus handles the vector search while the substring path is
measured separately.

An n-gram inverted index can narrow the candidate set before evaluating the full
pattern. The tradeoff is index size, write amplification, and sensitivity to the
chosen n-gram range. It also does not remove the need to validate the final match.

I would probably compare n-grams, a separate text index, and a different storage
layout against the same mixed semantic-and-exact query set. The unresolved tradeoff
is write amplification versus candidate-scan cost. Would love to hear your thoughts.

### Milvus mention basis

The source discusses substring filtering alongside Milvus vector search.

## Example: GPU build and CPU serving

### Title

Does separating GPU index construction from CPU query serving hold up operationally?

### Body

One concern I have is that graph-style ANN indexes can be expensive to build, while
keeping GPUs online for bursty query serving can be difficult to justify. One design
is to use GPU parallelism during construction, persist the resulting graph in a
CPU-friendly format, and serve Milvus queries from CPU replicas.

The architecture shifts cost toward build time, but it introduces compatibility,
artifact distribution, rebuild, and rollback questions. It may also behave
differently when updates are frequent rather than batch-oriented.

I would likely evaluate artifact movement, update freshness, CPU memory, and
cross-version compatibility separately before treating the split as an operational
win. Would love to hear your thoughts.

### Milvus mention basis

The source describes GPU index construction and CPU query serving for Milvus.
