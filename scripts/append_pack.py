#!/usr/bin/env python3
"""Validate Reddit draft packs without writing external state.

Reads JSON from stdin:
{
  "source_title": "...",
  "source_url": "https://...",
  "pool_blog_id": "optional",
  "items": [
    {
      "account_code": "R1",
      "content_type": "technical_post",
      "subreddit": "r/vectordatabase",
      "suggested_day": "2026-07-01",
      "title": "...",
      "body": "...",
      "disclosure": "",
      "link_policy": "no_link",
      "milvus_mention_basis": "The source-supported reason for the single body mention.",
      "angle": "..."
    }
  ]
}
"""
import json
import re
import sys
from pathlib import Path

import weekly_post_rules

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS = ROOT / "data" / "accounts.json"
LENGTH_RULES = ROOT / "data" / "content_length_rules.json"
USER_FINGERPRINTS = ROOT / "data" / "user_fingerprints.json"

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
ALLOWED_LINK_POLICIES = {"no_link"}

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
LANGUAGE_BUFFER_PATTERN = re.compile(
    r"\b(?:probably|one concern i have|my current view|i suspect|"
    r"i would (?:probably|likely)|i do not think|i don't think|i tend to|likely)\b",
    re.IGNORECASE,
)


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


def contains_any(text, phrases):
    lowered = (text or "").lower()
    return [p for p in phrases if p in lowered]


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
        link_policy = item.get("link_policy", "no_link") or "no_link"
        milvus_mention_basis = item.get("milvus_mention_basis", "") or ""
        voice_fingerprint = item.get("voice_fingerprint") or account.get("voice_fingerprint_id", "")
        combined = "\n".join([title, body, disclosure, milvus_mention_basis])
        length_tier = infer_length_tier(item)
        length_rule = length_rules.get(length_tier)
        fenced_code_blocks = code_blocks(body)
        account_policy = weekly_rules.get("account_policies", {}).get(code, {})

        if code not in active_accounts:
            errors.append(f"{prefix}: weekly posting is restricted to active accounts R1 and R2")

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

        if account_policy.get("identity_visibility") == "anonymous" and disclosure.strip():
            errors.append(
                f"{prefix}: {code} is anonymous; disclosure must stay empty and the draft must not reveal identity, employer, or affiliation"
            )

        if link_policy not in ALLOWED_LINK_POLICIES:
            errors.append(f"{prefix}: unknown link_policy {link_policy!r}")
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

        if voice_fingerprint and user_fingerprints and voice_fingerprint not in user_fingerprints:
            warnings.append(f"{prefix}: unknown voice_fingerprint {voice_fingerprint!r}")

        if content_type == "long_post":
            errors.append(f"{prefix}: long_post belongs in length_tier, not content_type; use content_type=technical_post or postmortem with length_tier=long_post")

        if not body.strip():
            errors.append(f"{prefix}: body is empty")
        else:
            opening_paragraph = re.split(r"\n\s*\n", body.strip(), maxsplit=1)[0]
            if not FIRST_PERSON_OPENING_PATTERN.search(opening_paragraph):
                warnings.append(
                    f"{prefix}: opening paragraph should establish the anonymous "
                    "first-person perspective immediately"
                )
            if not LANGUAGE_BUFFER_PATTERN.search(body):
                warnings.append(
                    f"{prefix}: add one or two natural language buffers such as "
                    "'probably', 'one concern I have', or 'my current view' "
                    "to calibrate personal judgments"
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
                errors.append(f"{prefix}: code blocks require length_tier=code_long_post")
            if len(fenced_code_blocks) > max_code_blocks:
                errors.append(f"{prefix}: too many code blocks for {length_tier} ({len(fenced_code_blocks)} > {max_code_blocks})")
            max_code_lines = int(length_rule.get("max_code_lines_total") or 0)
            if max_code_lines and code_line_count(body) > max_code_lines:
                errors.append(f"{prefix}: code is too long for Reddit review ({code_line_count(body)} lines > {max_code_lines})")
            good_subreddits = set(length_rule.get("good_subreddits", []))
            if subreddit and good_subreddits and subreddit not in good_subreddits:
                warnings.append(f"{prefix}: {length_tier} is unusual for {subreddit}")

        if content_type in ACTIVE_POST_CONTENT_TYPES and not title.strip():
            errors.append(f"{prefix}: title is required for post content")

        if has_url(title) or has_url(body):
            errors.append(f"{prefix}: R1/R2 drafts must not contain URLs in titles or body prose")
        if (item.get("approved_link") or "").strip():
            errors.append(f"{prefix}: approved_link is retired; R1 and R2 are both no-link")

        marketing = contains_any(combined, MARKETING_PHRASES)
        if marketing:
            errors.append(f"{prefix}: marketing phrases detected: {', '.join(marketing)}")

        brigade = contains_any(combined, VOTE_OR_BRIGADE_PHRASES)
        if brigade:
            errors.append(f"{prefix}: vote/brigade phrasing detected: {', '.join(brigade)}")

        title_milvus_mentions = len(MILVUS_PATTERN.findall(title))
        body_milvus_mentions = len(MILVUS_PATTERN.findall(body))
        mentions_zilliz = bool(ZILLIZ_PATTERN.search(combined))
        brand_policy = account.get("brand_policy", {})
        required_milvus_mentions = int(
            brand_policy.get("required_milvus_body_mentions") or 0
        )
        max_milvus_mentions = int(brand_policy.get("max_milvus_body_mentions") or 0)
        if title_milvus_mentions:
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
        if body_milvus_mentions and not brand_policy.get("may_mention_milvus"):
            errors.append(f"{prefix}: {code} is not allowed to mention Milvus")
        if body_milvus_mentions and not milvus_mention_basis.strip():
            errors.append(
                f"{prefix}: a Milvus body mention requires milvus_mention_basis describing the source-supported context"
            )
        if mentions_zilliz and not brand_policy.get("may_mention_zilliz"):
            errors.append(f"{prefix}: {code} is not allowed to mention Zilliz")
        if ANONYMITY_VIOLATION_PATTERN.search(combined):
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
