# r/Rag — current drafting guidance

## Scope

Use this community for retrieval quality, chunking, parsing, hybrid search,
reranking, evaluation, production RAG failures, local/self-hosted systems, and
tooling tradeoffs.

## Post Types

- `Tutorial`: step-by-step implementation, evaluation, debugging, or retrieval
  workflow. End with the final takeaway, verification step, or next action;
  do not add a question at the end.
- `Discussion`: a tradeoff, production failure, architecture choice, or open
  technical question. If inviting replies, use a soft conversational close
  such as `Would love to hear your thoughts.` rather than a hard question.
- `Tools & Resources`: a practical comparison or curated resource set with clear
  selection criteria.
- `Showcase`: a source-supported project or experiment with enough implementation
  detail to invite critique.

## Native structure

1. Open in first person and lead with the retrieval problem, not a product or
   blog summary. Keep the first-person setup source-supported.
2. Use occasional language buffers such as `probably`, `one concern I have`,
   or `my current view` for judgment calls; keep measured facts direct.
3. Include concrete constraints such as corpus size, update frequency, latency,
   filtering, evaluation method, cost, or operational burden.
4. Separate measured evidence from assumptions and unanswered questions.
5. State failure cases and tradeoffs.
6. Match the close to the Post Type: Tutorials do not end with questions;
   Discussions may invite comparable experience softly without forcing a
   question ending.

## Identity and brand boundary

- R1 is anonymous and `disclosure` stays empty.
- `I built` is allowed only when source-supported and without identity, employer,
  contributor/maintainer role, affiliation, customer identity, or project
  representation.
- The title must not mention Milvus. Every body must mention Milvus exactly once
  using source-supported technical background or data and must include a
  `milvus_mention_basis`. Never mention Zilliz.
- Screenshots provide Post Type and structural cues only.

## Links

R1 and R2 always use `no_link`. Never place a URL in the title, body, or a
separate approved-link field.

## Avoid

- predetermined winners or conclusions without retrieval evidence;
- invented experience, customers, benchmark numbers, or results;
- generic summaries without retrieval details;
- copying identities, links, disclosures, or exact wording from examples.
