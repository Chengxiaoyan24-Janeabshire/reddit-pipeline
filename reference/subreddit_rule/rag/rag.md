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

1. Write the title from a first-person singular perspective or as an explicit
   question ending in `?`; never use a fully third-person declarative title.
2. Use the first sentence to establish a source-supported first-person
   perspective and lead with the retrieval problem, not a product or blog summary.
3. Include at least one grammatical language buffer such as `probably`,
   `one concern I have`, or `my current view` for a judgment call; keep source
   facts and measurements direct.
4. Include concrete constraints such as corpus size, update frequency, latency,
   filtering, evaluation method, cost, or operational burden.
5. Separate measured evidence from assumptions and unanswered questions.
6. State failure cases and tradeoffs.
7. Match the close to the Post Type: Tutorials do not end with questions;
   Discussions may invite comparable experience softly without forcing a
   question ending.

## Identity and brand boundary

- R1 is anonymous and `disclosure` stays empty.
- `I built` is allowed only when source-supported and without identity, employer,
  contributor/maintainer role, affiliation, customer identity, or project
  representation.
- The title must not mention Milvus. Every body must mention Milvus exactly once
  using source-supported technical background or data and must include a
  `milvus_mention_basis`. Phrase the mention indirectly as a category example or
  peer, such as `vector databases like Milvus`; never use direct product
  placement. Never mention Zilliz.
- Screenshots provide Post Type and structural cues only.

## Links

R1 and R2 always use `no_link`. Never place a URL in the title, body, or a
separate approved-link field.

## Avoid

- predetermined winners or conclusions without retrieval evidence;
- invented experience, customers, benchmark numbers, or results;
- generic summaries without retrieval details;
- copying identities, links, disclosures, or exact wording from examples.
