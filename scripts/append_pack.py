#!/usr/bin/env python3
"""Validate Reddit draft packs without writing external state.

Reads JSON from stdin:
{
  "source_title": "...",
  "source_url": "https://...",
  "pool_blog_id": "optional",
  "items": [
    {
      "account_code": "<configured account>",
      "content_type": "technical_post",
      "subreddit": "<configured subreddit>",
      "suggested_day": "2026-07-01",
      "title": "What I learned about ...",
      "body": "...",
      "disclosure": "",
      "link_policy": "<guidance value>",
      "milvus_mention_basis": "The source-supported reason for the single body mention.",
      "angle": "..."
    }
  ]
}
"""
import json
import re
import sys

import resource_paths
import weekly_post_rules

ROOT = resource_paths.ROOT
ACCOUNTS = resource_paths.ACCOUNTS
LENGTH_RULES = resource_paths.CONTENT_LENGTH_RULES
USER_FINGERPRINTS = resource_paths.USER_FINGERPRINTS

URL_PATTERN = re.compile(r"https?://[^\s)]+", re.IGNORECASE)
CODE_FENCE_PATTERN = re.compile(r"```([a-zA-Z0-9_+-]*)")
MILVUS_PATTERN = re.compile(r"\bmilvus\b", re.IGNORECASE)
ZILLIZ_PATTERN = re.compile(r"\bzilliz\b", re.IGNORECASE)
ANONYMITY_VIOLATION_PATTERN = re.compile(
    r"\b(core contributor|project maintainer|employee|employer|affiliated|affiliation|"
    r"official account|founder|co-founder|creator of|author of|as a contributor|"
    r"as a maintainer|i(?:'m| am)(?: an?| the)? (?:contributor|maintainer)|"
    r"i contribute to|i contributed to|i maintain|i work at|i work for|"
    r"we work at|we work for|my company|our company|my startup|our team at)\b",
    re.IGNORECASE,
)
ACTIVE_POST_CONTENT_TYPES = {"technical_post", "comparison_post", "postmortem"}

MARKETING_PHRASES = [
    "check out milvus",
    "check out zilliz",
    "try milvus",
    "try zilliz",
    "book a demo",
    "sign up",
    "trusted by thousands",
    "fully managed milvus experience",
    "game changer",
    "best vector database",
    "go-to choice",
    "seamlessly scales",
]

VOTE_OR_BRIGADE_PHRASES = [
    "please upvote",
    "upvote this",
    "downvote",
    "boost this",
    "let's all comment",
]

FIRST_PERSON_OPENING_PATTERN = re.compile(
    r"\b(?:i|i'm|i’ve|i've|i'd|i’d|my)\b",
    re.IGNORECASE,
)
FIRST_PERSON_TITLE_PATTERN = re.compile(
    r"\b(?:i|i'm|i’ve|i've|i'd|i’d|i’ll|i'll|my|me)\b",
    re.IGNORECASE,
)
LANGUAGE_BUFFER_PATTERN = re.compile(
    r"\b(?:probably|one concern i have|my current view|i suspect|"
    r"i would (?:probably|likely)|i do not think|i don't think|i tend to|"
    r"i(?:'m| am) (?:concerned|not convinced)|it probably depends(?: on)?|likely)\b",
    re.IGNORECASE,
)
UNGRAMMATICAL_LANGUAGE_BUFFER_PATTERN = re.compile(
    r"\b(?:probably\s+)?i concern\b",
    re.IGNORECASE,
)
MILVUS_PEER_CATEGORY = (
    r"(?:vector\s+databases?|data\s+infrastructures?|database\s+systems?|"
    r"data\s+platforms?|retrieval\s+(?:systems?|backends?|infrastructures?)|"
    r"vector\s+stores?|storage\s+(?:systems?|engines?)|databases?)"
)
NATURAL_MILVUS_CONTEXT_PATTERNS = [
    re.compile(
        rf"\b{MILVUS_PEER_CATEGORY}\b\s*,?\s*"
        rf"(?:such\s+as|like|including)\s+\bmilvus\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bmilvus\b\s*,?\s*(?:and|or|alongside)\s+"
        rf"(?:other\s+)?\b{MILVUS_PEER_CATEGORY}\b",
        re.IGNORECASE,
    ),
]


def load_accounts():
    return {a["account_code"]: a for a in json.loads(ACCOUNTS.read_text())}


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def load_length_rules():
    if not LENGTH_RULES.exists():
        return {}
    return {r["tier"]: r for r in json.loads(LENGTH_RULES.read_text())}


def load_user_fingerprints():
    rows = load_json(USER_FINGERPRINTS, [])
    return {
        row.get("fingerprint_id"): row
        for row in rows
        if row.get("fingerprint_id")
    }


def has_url(text):
    return bool(URL_PATTERN.search(text or ""))


def normalize_body(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def first_sentence(text):
    stripped = (text or "").strip()
    if not stripped:
        return ""
    match = re.search(r"[.!?](?:[\"'”’)]*)?(?=\s|$)", stripped)
    if match:
        return stripped[: match.end()]
    return re.split(r"\n+", stripped, maxsplit=1)[0]


def contains_any(text, phrases):
    lowered = (text or "").lower()
    return [p for p in phrases if p in lowered]


def title_has_personal_or_question_perspective(title):
    text = (title or "").strip()
    return bool(
        text
        and (
            FIRST_PERSON_TITLE_PATTERN.search(text)
            or text.endswith(("?", "？"))
        )
    )


def has_natural_milvus_context(text):
    return any(pattern.search(text or "") for pattern in NATURAL_MILVUS_CONTEXT_PATTERNS)


def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def code_blocks(text):
    langs = []
    in_code = False
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("```"):
            continue
        if not in_code:
            match = CODE_FENCE_PATTERN.match(stripped)
            langs.append((match.group(1) if match else "").lower())
        in_code = not in_code
    return langs


def code_line_count(text):
    total = 0
    in_code = False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            total += 1
    return total


def infer_length_tier(item):
    explicit = item.get("length_tier")
    if explicit:
        return explicit
    content_type = item.get("content_type", "")
    body = item.get("body", "") or item.get("post", "")
    if code_blocks(body) or item.get("code_language"):
        return "code_long_post"
    words = word_count(body)
    if content_type == "postmortem" or words >= 420:
        return "long_post"
    if words and words < 140:
        return "short_post"
    return "standard_post"


def infer_code_language(item):
    if item.get("code_language"):
        return item["code_language"]
    body = item.get("body", "") or item.get("post", "")
    langs = [lang for lang in code_blocks(body) if lang]
    return (langs[0].lower() if langs else "")


def validate(spec):
    accounts = load_accounts()
    length_rules = load_length_rules()
    user_fingerprints = load_user_fingerprints()
    weekly_rules = weekly_post_rules.load_rules()
    active_accounts = set(weekly_rules.get("active_accounts", []))
    subreddit_slots = weekly_post_rules.slots_by_subreddit(weekly_rules)
    errors = []
    warnings = []

    items = spec.get("items") or []
    if not items:
        errors.append("spec.items is empty")
        return errors, warnings

    seen_bodies = {}
    account_day = set()

    for idx, item in enumerate(items, 1):
        prefix = f"items[{idx}]"
        code = item.get("account_code", "")
        account = accounts.get(code)
        if not account:
            errors.append(f"{prefix}: unknown account_code {code!r}")
            continue

        content_type = item.get("content_type", "")
        subreddit = item.get("subreddit", "")
        post_type = item.get("post_type", "") or ""
        title = item.get("title", "") or ""
        body = item.get("body", "") or item.get("post", "") or ""
        disclosure = item.get("disclosure", "") or ""
        link_policy = item.get("link_policy") or weekly_post_rules.recommend_link_policy(
            code, subreddit, post_type, weekly_rules
        )
        milvus_mention_basis = item.get("milvus_mention_basis", "") or ""
        expected_voice_fingerprint = account.get("voice_fingerprint_id", "")
        voice_fingerprint = item.get("voice_fingerprint") or expected_voice_fingerprint
        combined = "\n".join(
            [title, body, disclosure, milvus_mention_basis, item.get("angle", "") or ""]
        )
        length_tier = infer_length_tier(item)
        length_rule = length_rules.get(length_tier)
        fenced_code_blocks = code_blocks(body)
        account_policy = weekly_rules.get("account_policies", {}).get(code, {})
        title_policy = weekly_rules.get("title_perspective_policy", {})
        opening_policy = weekly_rules.get("opening_perspective_policy", {})
        language_buffer_policy = weekly_rules.get("language_buffer_policy", {})
        milvus_context_policy = weekly_rules.get("milvus_mention_context_policy", {})

        if code not in active_accounts:
            errors.append(
                f"{prefix}: account is not active for the current weekly workflow; "
                f"choose one of {sorted(active_accounts)}"
            )

        if content_type not in ACTIVE_POST_CONTENT_TYPES:
            errors.append(
                f"{prefix}: current weekly workflow only accepts technical post content types "
                f"{sorted(ACTIVE_POST_CONTENT_TYPES)}"
            )

        allowed_subreddits = weekly_post_rules.allowed_subreddits(code, weekly_rules)
        if subreddit not in allowed_subreddits:
            errors.append(
                f"{prefix}: {code} may only post to {sorted(allowed_subreddits)}; got {subreddit!r}"
            )

        slot = subreddit_slots.get(subreddit)
        allowed_post_types = (slot or {}).get("post_types", [])
        if not post_type:
            errors.append(f"{prefix}: post_type is required for weekly post review metadata")
        elif allowed_post_types and post_type not in allowed_post_types:
            errors.append(
                f"{prefix}: post_type {post_type!r} is invalid for {subreddit}; "
                f"choose one of {allowed_post_types}"
            )
        elif post_type:
            recommended_post_type = weekly_post_rules.recommend_post_type(
                subreddit, "\n".join([title, item.get("angle", ""), body]), weekly_rules
            )
            if recommended_post_type and recommended_post_type != post_type:
                warnings.append(
                    f"{prefix}: topic/framing signals look closer to Post Type "
                    f"{recommended_post_type!r} than {post_type!r}; review the subreddit screenshots before publishing"
                )
        if (
            code == "R2"
            and weekly_post_rules.is_r2_question_post(subreddit, post_type, weekly_rules)
        ):
            if length_tier and length_tier != "short_post":
                errors.append(
                    f"{prefix}: R2 short question post for {subreddit!r} must use "
                    "length_tier 'short_post'"
                )
            if title and not title.endswith(("?", "？")):
                errors.append(
                    f"{prefix}: R2 short question post for {subreddit!r} must use "
                    "an explicit question title ending in '?'"
                )

        if account_policy.get("identity_visibility") == "anonymous" and disclosure.strip():
            errors.append(
                f"{prefix}: {code} is anonymous; disclosure must stay empty and the draft must not reveal identity, employer, or affiliation"
            )

        link_policy_modes = weekly_rules.get("link_policy_modes", {})
        if link_policy not in link_policy_modes:
            errors.append(
                f"{prefix}: unknown link_policy {link_policy!r}; choose one of "
                f"{sorted(link_policy_modes)}"
            )
        else:
            allowed_link_policies = weekly_post_rules.allowed_link_policies(
                code, subreddit, post_type, weekly_rules
            )
            if link_policy not in allowed_link_policies:
                errors.append(
                    f"{prefix}: link_policy {link_policy!r} is not allowed for "
                    f"{code} in {subreddit} with Post Type {post_type!r}; "
                    f"choose one of {sorted(allowed_link_policies)}"
                )

        if expected_voice_fingerprint and voice_fingerprint != expected_voice_fingerprint:
            errors.append(
                f"{prefix}: {code} must use voice_fingerprint "
                f"{expected_voice_fingerprint!r}; got {voice_fingerprint!r}"
            )
        if (
            expected_voice_fingerprint
            and user_fingerprints
            and expected_voice_fingerprint not in user_fingerprints
        ):
            errors.append(
                f"{prefix}: configured voice_fingerprint "
                f"{expected_voice_fingerprint!r} is missing from "
                "reference/accounts/user_fingerprints.json"
            )

        if content_type in length_rules:
            errors.append(
                f"{prefix}: {content_type} belongs in length_tier, not "
                "content_type; use a configured content type and set the tier "
                "separately"
            )

        if not body.strip():
            errors.append(f"{prefix}: body is empty")
        else:
            opening_sentence = first_sentence(body)
            if (
                opening_policy.get("scope") == "first_sentence"
                and not FIRST_PERSON_OPENING_PATTERN.search(opening_sentence)
            ):
                target = (
                    errors
                    if opening_policy.get("severity", "error") == "error"
                    else warnings
                )
                target.append(
                    f"{prefix}: the first sentence must establish the configured "
                    "first-person perspective"
                )
            if UNGRAMMATICAL_LANGUAGE_BUFFER_PATTERN.search(body):
                errors.append(
                    f"{prefix}: 'I concern' is not a grammatical language buffer; "
                    "use phrasing such as 'one concern I have', 'I am concerned', "
                    "or 'I would probably'"
                )
            elif (
                int(language_buffer_policy.get("minimum_matches_per_body") or 0)
                > len(list(LANGUAGE_BUFFER_PATTERN.finditer(body)))
            ):
                target = (
                    errors
                    if language_buffer_policy.get("severity", "error") == "error"
                    else warnings
                )
                target.append(
                    f"{prefix}: body must include at least "
                    f"{int(language_buffer_policy.get('minimum_matches_per_body') or 0)} "
                    "grammatical language buffer match(es), such as "
                    "'probably', 'one concern I have', or 'my current view' "
                    "for a personal judgment; do not hedge source-supported facts "
                    "or measurements"
                )
            if post_type == "Tutorial" and body.rstrip().endswith("?"):
                errors.append(
                    f"{prefix}: Tutorial posts must end with a takeaway or next "
                    "step, not a question"
                )
            if post_type == "Discussion" and body.rstrip().endswith("?"):
                warnings.append(
                    f"{prefix}: Discussion ending is too interrogative; state the "
                    "uncertainty and close with a soft invitation such as "
                    "'Would love to hear your thoughts.'"
                )

        if length_rules and not length_rule:
            errors.append(f"{prefix}: unknown length_tier {length_tier!r}")
        elif length_rule:
            words = word_count(body)
            min_words = int(length_rule.get("min_words") or 0)
            max_words = int(length_rule.get("max_words") or 0)
            if words and min_words and words < min_words:
                warnings.append(f"{prefix}: {length_tier} is short ({words} words, target {length_rule.get('target_words')})")
            if max_words and words > max_words:
                warnings.append(f"{prefix}: {length_tier} is long ({words} words, target {length_rule.get('target_words')})")
            max_code_blocks = int(length_rule.get("max_code_blocks") or 0)
            if fenced_code_blocks and not length_rule.get("code_allowed"):
                code_tiers = sorted(
                    tier
                    for tier, rule in length_rules.items()
                    if rule.get("code_allowed")
                )
                errors.append(
                    f"{prefix}: code blocks require a code-enabled length tier; "
                    f"choose one of {code_tiers}"
                )
            if len(fenced_code_blocks) > max_code_blocks:
                errors.append(f"{prefix}: too many code blocks for {length_tier} ({len(fenced_code_blocks)} > {max_code_blocks})")
            max_code_lines = int(length_rule.get("max_code_lines_total") or 0)
            if max_code_lines and code_line_count(body) > max_code_lines:
                errors.append(f"{prefix}: code is too long for Reddit review ({code_line_count(body)} lines > {max_code_lines})")
        if content_type in ACTIVE_POST_CONTENT_TYPES and not title.strip():
            errors.append(f"{prefix}: title is required for post content")
        elif (
            title_policy.get("require_first_person_or_question")
            and not title_has_personal_or_question_perspective(title)
        ):
            errors.append(
                f"{prefix}: title must use a first-person perspective such as "
                "'I think'/'Now I believe', or be an explicit question ending in '?'"
            )

        link_mode = weekly_rules.get("link_policy_modes", {}).get(link_policy, {})
        approved_link = (item.get("approved_link") or "").strip()
        if not link_mode.get("allow_inline_urls") and (has_url(title) or has_url(body)):
            errors.append(
                f"{prefix}: link_policy {link_policy!r} does not allow URLs in "
                "titles or body prose"
            )
        if approved_link and not link_mode.get("allow_approved_link"):
            errors.append(
                f"{prefix}: link_policy {link_policy!r} does not allow approved_link"
            )
        if link_mode.get("require_approved_link") and not approved_link:
            errors.append(
                f"{prefix}: link_policy {link_policy!r} requires approved_link"
            )

        marketing = contains_any(combined, MARKETING_PHRASES)
        if marketing:
            errors.append(f"{prefix}: marketing phrases detected: {', '.join(marketing)}")

        brigade = contains_any(combined, VOTE_OR_BRIGADE_PHRASES)
        if brigade:
            errors.append(f"{prefix}: vote/brigade phrasing detected: {', '.join(brigade)}")

        title_milvus_mentions = len(MILVUS_PATTERN.findall(title))
        body_milvus_mentions = len(MILVUS_PATTERN.findall(body))
        mentions_zilliz = bool(ZILLIZ_PATTERN.search(combined))
        required_milvus_mentions = int(
            account_policy.get("required_milvus_body_mentions") or 0
        )
        max_milvus_mentions = int(
            account_policy.get("max_milvus_body_mentions") or 0
        )
        if title_milvus_mentions and not milvus_context_policy.get("allow_in_title"):
            errors.append(f"{prefix}: Milvus may appear only in the body, not the title")
        if required_milvus_mentions and body_milvus_mentions != required_milvus_mentions:
            required_text = (
                "exactly once"
                if required_milvus_mentions == 1
                else f"exactly {required_milvus_mentions} times"
            )
            errors.append(
                f"{prefix}: body must mention Milvus {required_text}; "
                f"found {body_milvus_mentions}"
            )
        elif body_milvus_mentions > max_milvus_mentions:
            errors.append(
                f"{prefix}: body may mention Milvus at most {max_milvus_mentions} time(s); "
                f"found {body_milvus_mentions}"
            )
        if body_milvus_mentions and not account_policy.get("may_mention_milvus"):
            errors.append(f"{prefix}: {code} is not allowed to mention Milvus")
        if (
            body_milvus_mentions
            and milvus_context_policy.get("require_basis")
            and not milvus_mention_basis.strip()
        ):
            errors.append(
                f"{prefix}: a Milvus body mention requires milvus_mention_basis describing the source-supported context"
            )
        if (
            body_milvus_mentions
            and milvus_context_policy.get("mode") == "category_example_or_peer_group"
            and not has_natural_milvus_context(body)
        ):
            errors.append(
                f"{prefix}: the Milvus mention must be indirect and contextual, "
                "for example 'vector databases like Milvus', "
                "'data infrastructures such as Milvus', or "
                "'Milvus and other databases'; direct product placement is not allowed"
            )
        if mentions_zilliz and not account_policy.get("may_mention_zilliz"):
            errors.append(f"{prefix}: {code} is not allowed to mention Zilliz")

        brand_policy = weekly_rules.get("brand_mention_policy", {})
        if brand_policy.get("allow_tech_stack_brand_names"):
            database_brand_policy = brand_policy.get("database_brand_mentions", {})
            allowed_named_database_post_types = set(
                database_brand_policy.get("allow_in_post_types") or []
            )
            blocked_brands = [
                name
                for name in (database_brand_policy.get("blocked_named_brands") or [])
                if name
            ]
            if post_type not in allowed_named_database_post_types:
                for brand in blocked_brands:
                    pattern = re.compile(rf"\b{re.escape(brand)}\b", re.IGNORECASE)
                    if pattern.search(title) or pattern.search(body):
                        errors.append(
                            f"{prefix}: named database brand {brand!r} is only allowed in "
                            f"question posts {sorted(allowed_named_database_post_types)}; "
                            "in other posts refer to other databases as a peer group"
                        )
        if (
            account_policy.get("identity_visibility") == "anonymous"
            and ANONYMITY_VIOLATION_PATTERN.search(combined)
        ):
            errors.append(
                f"{prefix}: anonymous drafts must not reveal an employer, company, contributor/maintainer role, or affiliation"
            )

        norm = normalize_body(body)
        if norm in seen_bodies:
            errors.append(f"{prefix}: duplicate body also used by {seen_bodies[norm]}")
        else:
            seen_bodies[norm] = prefix

        day_key = (code, item.get("suggested_day", ""))
        if day_key[1] and day_key in account_day:
            warnings.append(f"{prefix}: same account has multiple drafts on {day_key[1]}")
        account_day.add(day_key)

        if len(title) > 180:
            warnings.append(f"{prefix}: title is long for mobile ({len(title)} chars)")
        if content_type in {"technical_post", "comparison_post", "postmortem"} and len(body) < 180:
            warnings.append(f"{prefix}: technical body may be too thin ({len(body)} chars)")
        if subreddit and not subreddit.startswith("r/"):
            warnings.append(f"{prefix}: subreddit should look like r/name")

    return errors, warnings


def main():
    try:
        spec = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        sys.exit(1)

    errors, warnings = validate(spec)
    if errors:
        print(json.dumps({"ok": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps({
        "ok": True,
        "validated": len(spec.get("items", [])),
        "warnings": warnings,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
