# r/Rag — current drafting guidance

## Scope

Use this community for retrieval quality, chunking, parsing, hybrid search,
reranking, evaluation, production RAG failures, local/self-hosted systems, and
tooling tradeoffs.

## Post Types

- `Tutorial`: step-by-step implementation, evaluation, debugging, or retrieval
  workflow.
- `Discussion`: a tradeoff, production failure, architecture choice, or open
  technical question.
- `Tools & Resources`: a practical comparison or curated resource set with clear
  selection criteria.
- `Showcase`: a source-supported project or experiment with enough implementation
  detail to invite critique.

## Native structure

1. Lead with the retrieval problem, not a product or blog summary.
2. Include concrete constraints such as corpus size, update frequency, latency,
   filtering, evaluation method, cost, or operational burden.
3. Separate measured evidence from assumptions and unanswered questions.
4. State failure cases and tradeoffs.
5. Keep an open question when it naturally invites comparable experience; a
   question ending is optional.

## Identity and brand boundary

- R1 is anonymous and `disclosure` stays empty.
- `I built` is allowed only when source-supported and without identity, employer,
  contributor/maintainer role, affiliation, customer identity, or project
  representation.
- The title must not mention Milvus. The body may mention Milvus once only when
  the technical background or data is source-supported. Never mention Zilliz.
- Screenshots provide Post Type and structural cues only.

## Links

R1 and R2 always use `no_link`. Never place a URL in the title, body, or a
separate approved-link field.

## Avoid

- predetermined winners or conclusions without retrieval evidence;
- invented experience, customers, benchmark numbers, or results;
- generic summaries without retrieval details;
- copying identities, links, disclosures, or exact wording from examples.
