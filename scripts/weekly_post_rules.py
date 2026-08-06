#!/usr/bin/env python3
"""Load and apply the fixed weekly Reddit account/subreddit/post-type rules."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data" / "weekly_post_rules.json"


def load_rules():
    return json.loads(RULES_PATH.read_text())


def source_recency_policy(rules=None):
    rules = rules or load_rules()
    return rules.get("source_recency_policy", {})


def priority_window_days(rules=None):
    policy = source_recency_policy(rules)
    return max(1, int(policy.get("priority_window_days", 7)))


def publish_datetime(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def recent_cutoff(as_of=None, rules=None):
    now = publish_datetime(as_of) or datetime.now(timezone.utc)
    return now - timedelta(days=priority_window_days(rules))


def is_recent_source(publish_date, as_of=None, rules=None):
    published_at = publish_datetime(publish_date)
    return bool(published_at and published_at >= recent_cutoff(as_of, rules))


def source_priority_key(publish_date, as_of=None, rules=None):
    published_at = publish_datetime(publish_date)
    if not published_at:
        return (2, 0)
    return (
        0 if is_recent_source(published_at, as_of, rules) else 1,
        -published_at.timestamp(),
    )


def slots_by_subreddit(rules=None):
    rules = rules or load_rules()
    return {slot["subreddit"]: slot for slot in rules.get("weekly_slots", [])}


def slot_for(subreddit, rules=None):
    return slots_by_subreddit(rules).get(subreddit)


def allowed_subreddits(account_code, rules=None):
    rules = rules or load_rules()
    return {
        slot["subreddit"]
        for slot in rules.get("weekly_slots", [])
        if slot.get("account_code") == account_code
    }


def recommend_post_type(subreddit, text, rules=None):
    rules = rules or load_rules()
    slot = slots_by_subreddit(rules).get(subreddit)
    if not slot:
        return ""

    allowed = slot.get("post_types", [])
    default = slot.get("default_post_type", "")
    if allowed == ["No fixed post type"]:
        return allowed[0]

    lowered = re.sub(r"\s+", " ", (text or "")).lower()
    scored = []
    for post_type in allowed:
        post_rule = slot.get("post_type_rules", {}).get(post_type, {})
        score = sum(1 for term in post_rule.get("signals", []) if term.lower() in lowered)
        scored.append((score, post_type))
    scored.sort(key=lambda row: (-row[0], allowed.index(row[1])))
    return scored[0][1] if scored and scored[0][0] > 0 else default


def post_type_rule(subreddit, post_type, rules=None):
    rules = rules or load_rules()
    slot = slot_for(subreddit, rules)
    if not slot:
        return {}
    return slot.get("post_type_rules", {}).get(post_type, {})


def allowed_link_policies(account_code, subreddit, post_type, rules=None):
    rules = rules or load_rules()
    account_policy = rules.get("account_policies", {}).get(account_code, {})
    if account_policy.get("link_mode") == "no_link":
        return {"no_link"}
    return set(
        post_type_rule(subreddit, post_type, rules).get(
            "allowed_link_policies", ["no_link"]
        )
    )


def recommend_link_policy(account_code, subreddit, post_type, rules=None):
    rules = rules or load_rules()
    allowed = allowed_link_policies(account_code, subreddit, post_type, rules)
    if allowed == {"no_link"}:
        return "no_link"
    default = post_type_rule(subreddit, post_type, rules).get(
        "default_link_policy", "no_link"
    )
    return default if default in allowed else "no_link"


def main():
    print(json.dumps(load_rules(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
