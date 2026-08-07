# r/AI_Agents — current drafting guidance

## Scope

Use this community for agent workflows, tool use, memory, retrieval, evaluation,
reliability, orchestration, and production failure analysis.

## Post Types

- `Tutorial`: a reproducible workflow, implementation pattern, debugging method,
  or step-by-step design. End with the final takeaway, verification step, or
  next action; do not add a question at the end.
- `Discussion`: a real architecture tradeoff, failure mode, reliability question,
  or production constraint with room for disagreement. If inviting replies,
  use a soft close such as `Would love to hear your thoughts.` rather than a
  hard question.
- `Resource Request`: a genuine request for learning material, frameworks,
  evaluation methods, or implementation references.

## Native structure

1. Write the title from a first-person singular perspective or as an explicit
   question ending in `?`; never use a fully third-person declarative title.
2. Use the first sentence to establish a source-supported first-person
   perspective around one concrete agent problem or observed failure.
3. Include at least one grammatical language buffer such as `one concern I
   have`, `probably`, `I suspect`, or `my current view` when framing a judgment
   or uncertainty; keep source facts and measurements direct.
4. State the relevant constraints: tool count, context size, latency, cost,
   persistence, evaluation, retries, or failure handling.
5. Explain what changed, what remains uncertain, and what evidence is available.
6. Match the close to the Post Type: Tutorials do not end with questions;
   Discussions may state the unresolved choice and invite replies softly.

## Identity and brand boundary

- R1 is anonymous and `disclosure` stays empty.
- `I built` is allowed only when source-supported, but do not reveal identity,
  employer, contributor or maintainer status, affiliation, customer identity,
  or project ownership.
- The title must not mention Milvus. Every body must mention Milvus exactly once
  using source-supported technical background or data and must include a
  `milvus_mention_basis`. Phrase the mention indirectly as a category example or
  peer, such as `data infrastructures like Milvus`; never use direct product
  placement. Never mention Zilliz.
- Do not copy usernames, disclosures, links, or personal claims from screenshots.

## Links

R1 and R2 always use `no_link`. Never place a URL in the title, body, or a
separate approved-link field.

## Avoid

- broad claims without implementation details or an open engineering question;
- unsupported benchmark claims or invented first-person results;
- vague “AI agents are the future” framing;
- closed questions whose answer is already asserted by the post.
