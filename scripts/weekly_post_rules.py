#!/usr/bin/env python3
"""Load and apply the fixed weekly Reddit account/subreddit/post-type rules."""
import json
import re
from datetime import datetime, timedelta, timezone

import resource_paths

WORKFLOW_PATH = resource_paths.WEEKLY_WORKFLOW
GUIDANCE_PATH = resource_paths.EDITORIAL_POLICY
EXPECTED_INSTRUCTION_LEVELS = {
    "guidance": (
        "disclosure",
        "first_person_language",
        "language_buffer",
    ),
    "subreddit": (
        "subreddit_subrules",
        "post_category",
        "post_type",
        "native_structure",
        "native_style",
    ),
    "audience_angle": (
        "preferred_technical_angle",
        "topic_fit",
        "voice_fingerprint",
    ),
}


def load_rules():
    workflow = json.loads(WORKFLOW_PATH.read_text())
    guidance = json.loads(GUIDANCE_PATH.read_text())
    overlap = set(workflow).intersection(guidance)
    if overlap:
        names = ", ".join(sorted(overlap))
        raise ValueError(f"Workflow and guidance keys must not overlap: {names}")
    rules = {**guidance, **workflow}
    validate_contract(rules)
    return rules


def validate_contract(rules):
    errors = []
    slots = rules.get("weekly_slots", [])
    pack_size = int(rules.get("weekly_pack_size") or 0)
    active_accounts = set(rules.get("active_accounts", []))
    link_modes = set(rules.get("link_policy_modes", {}))
    pairs = [(slot.get("account_code"), slot.get("subreddit")) for slot in slots]

    precedence = rules.get("instruction_precedence")
    if not isinstance(precedence, dict):
        errors.append("instruction_precedence must be defined by editorial guidance")
    else:
        if precedence.get("conflict_resolution") != "higher_level_wins":
            errors.append(
                "instruction_precedence conflict_resolution must be "
                "'higher_level_wins'"
            )
        if precedence.get("unresolvable_conflict") != "reject":
            errors.append(
                "instruction_precedence unresolvable_conflict must be 'reject'"
            )
        if not str(precedence.get("source_fact_boundary") or "").strip():
            errors.append("instruction_precedence must preserve a source_fact_boundary")

        levels = precedence.get("levels")
        if not isinstance(levels, list) or not all(
            isinstance(level, dict) for level in levels
        ):
            errors.append("instruction_precedence levels must be an ordered list")
        else:
            expected_ids = list(EXPECTED_INSTRUCTION_LEVELS)
            actual_ids = [level.get("id") for level in levels]
            if actual_ids != expected_ids:
                errors.append(
                    "instruction_precedence level order must be "
                    f"{expected_ids}; got {actual_ids}"
                )
            for rank, level_id in enumerate(expected_ids, start=1):
                matching = next(
                    (level for level in levels if level.get("id") == level_id),
                    None,
                )
                if not matching:
                    continue
                if matching.get("rank") != rank:
                    errors.append(
                        f"instruction_precedence {level_id!r} rank must be {rank}"
                    )
                controls = matching.get("controls")
                expected_controls = list(EXPECTED_INSTRUCTION_LEVELS[level_id])
                if controls != expected_controls:
                    errors.append(
                        f"instruction_precedence {level_id!r} controls must be "
                        f"{expected_controls}; got {controls}"
                    )

    if pack_size != len(slots):
        errors.append(
            f"weekly_pack_size is {pack_size}, but weekly_slots contains {len(slots)} rows"
        )
    if len(set(pairs)) != len(pairs):
        errors.append("weekly_slots contains duplicate account/subreddit pairs")

    for slot in slots:
        account_code = slot.get("account_code")
        subreddit = slot.get("subreddit")
        post_types = slot.get("post_types", [])
        if account_code not in active_accounts:
            errors.append(f"{account_code!r} for {subreddit!r} is not active")

        if slot.get("default_post_type") not in post_types:
            errors.append(f"{subreddit!r} default_post_type is not in post_types")

        rule_json = slot.get("rule_json")
        if not rule_json:
            errors.append(f"{subreddit!r} has no rule_json")
        else:
            rule_path = resource_paths.ROOT / rule_json
            try:
                slot_rule = json.loads(rule_path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{subreddit!r} rule_json cannot be loaded: {exc}")
            else:
                if slot_rule.get("subreddit") != subreddit:
                    errors.append(
                        f"{subreddit!r} rule_json declares "
                        f"{slot_rule.get('subreddit')!r}"
                    )
                described_post_types = set(
                    slot_rule.get("post_type_guidance", {})
                )
                if described_post_types != set(post_types):
                    errors.append(
                        f"{subreddit!r} rule_json Post Types must match weekly "
                        f"post_types; got {sorted(described_post_types)}"
                    )

        review_markdown = slot.get("review_markdown")
        if not review_markdown:
            errors.append(f"{subreddit!r} has no review_markdown")
        for post_type, post_rule in slot.get("post_type_rules", {}).items():
            unknown = set(post_rule.get("allowed_link_policies", [])) - link_modes
            if unknown:
                errors.append(
                    f"{subreddit!r} / {post_type!r} uses unknown link policies "
                    f"{sorted(unknown)}"
                )

    r2_policy = rules.get("r2_short_question_policy")
    if r2_policy:
        if r2_policy.get("enabled"):
            if r2_policy.get("account_code") != "R2":
                errors.append("r2_short_question_policy must target account R2")
            if int(r2_policy.get("weekly_count") or 0) != 1:
                errors.append("r2_short_question_policy weekly_count must be 1")
            question_post_types = r2_policy.get("question_post_types") or {}
            for subreddit, post_type in question_post_types.items():
                slot = next(
                    (s for s in slots if s.get("subreddit") == subreddit),
                    None,
                )
                if not slot:
                    errors.append(
                        f"r2_short_question_policy references unknown subreddit "
                        f"{subreddit!r}"
                    )
                elif slot.get("account_code") != "R2":
                    errors.append(
                        f"r2_short_question_policy subreddit {subreddit!r} is not "
                        "an R2 slot"
                    )
                elif post_type not in slot.get("post_types", []):
                    errors.append(
                        f"r2_short_question_policy post type {post_type!r} is not "
                        f"valid for {subreddit!r}"
                    )

    for account_code in active_accounts:
        account_policy = rules.get("account_policies", {}).get(account_code)
        if not account_policy:
            errors.append(f"active account {account_code!r} has no editorial policy")
            continue
        account_mode = account_policy.get("link_mode")
        if account_mode and account_mode != "per_post_type" and account_mode not in link_modes:
            errors.append(
                f"active account {account_code!r} uses unknown link mode {account_mode!r}"
            )

    if errors:
        raise ValueError("Invalid merged Reddit workflow/guidance contract: " + "; ".join(errors))


def r2_short_question_policy(rules=None):
    rules = rules or load_rules()
    return rules.get("r2_short_question_policy") or {}


def r2_question_post_type_for(subreddit, rules=None):
    policy = r2_short_question_policy(rules)
    return (policy.get("question_post_types") or {}).get(subreddit, "")


def is_r2_question_post(subreddit, post_type, rules=None):
    expected = r2_question_post_type_for(subreddit, rules)
    return bool(expected and post_type == expected)


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
    account_mode = account_policy.get("link_mode")
    if account_mode and account_mode != "per_post_type":
        return {account_mode}
    return set(
        post_type_rule(subreddit, post_type, rules).get(
            "allowed_link_policies", []
        )
    )


def recommend_link_policy(account_code, subreddit, post_type, rules=None):
    rules = rules or load_rules()
    allowed = allowed_link_policies(account_code, subreddit, post_type, rules)
    account_default = (
        rules.get("account_policies", {})
        .get(account_code, {})
        .get("default_link_policy")
    )
    default = post_type_rule(subreddit, post_type, rules).get(
        "default_link_policy"
    )
    for candidate in (default, account_default):
        if candidate in allowed:
            return candidate
    return sorted(allowed)[0] if allowed else ""


def main():
    print(json.dumps(load_rules(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
