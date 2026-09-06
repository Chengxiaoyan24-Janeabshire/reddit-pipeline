#!/usr/bin/env python3
"""Load and apply the fixed weekly Reddit account/subreddit/post-type rules."""
import json
import re
from datetime import datetime, timedelta, timezone

import resource_paths

WORKFLOW_PATH = resource_paths.WEEKLY_WORKFLOW
GUIDANCE_PATH = resource_paths.EDITORIAL_POLICY
ROUTES_PATH = resource_paths.EDITORIAL_ROUTES
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
    routing = json.loads(ROUTES_PATH.read_text())
    route_guidance = {}
    for route_id, route in routing.get("routes", {}).items():
        guidance_path = resource_paths.ROOT / route["guidance"]
        route_guidance[route_id] = json.loads(guidance_path.read_text())
    overlap = set(workflow).intersection(guidance)
    if overlap:
        names = ", ".join(sorted(overlap))
        raise ValueError(f"Workflow and guidance keys must not overlap: {names}")
    rules = {
        **guidance,
        **workflow,
        "editorial_routing": routing,
        "editorial_routes": route_guidance,
    }
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
        allowed_accounts = slot.get("allowed_accounts") or [account_code]
        if account_code not in allowed_accounts:
            errors.append(
                f"{subreddit!r} allowed_accounts must include its owning account "
                f"{account_code!r}"
            )
        unknown_allowed = set(allowed_accounts) - active_accounts
        if unknown_allowed:
            errors.append(
                f"{subreddit!r} allows inactive accounts {sorted(unknown_allowed)}"
            )

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
            if r2_policy.get("scope") != "anonymous_route_only":
                errors.append(
                    "r2_short_question_policy must apply only to the anonymous route"
                )
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

    anonymous_scoped_policies = (
        "title_perspective_policy",
        "title_hook_policy",
        "language_buffer_policy",
        "milvus_mention_context_policy",
    )
    for policy_name in anonymous_scoped_policies:
        if (rules.get(policy_name) or {}).get("scope") != "anonymous_route_only":
            errors.append(f"{policy_name} must apply only to the anonymous route")
    if (rules.get("opening_perspective_policy") or {}).get("route_scope") != "anonymous_route_only":
        errors.append(
            "opening_perspective_policy must apply only to the anonymous route"
        )
    surface_policy = rules.get("pack_surface_variation_policy") or {}
    if surface_policy.get("scope") != "anonymous_weekly_pack":
        errors.append(
            "pack_surface_variation_policy must apply to the anonymous weekly pack"
        )
    if int(surface_policy.get("max_drafts_per_scaffold") or 0) != 1:
        errors.append(
            "pack_surface_variation_policy max_drafts_per_scaffold must be 1"
        )

    for account_code in active_accounts:
        account_policy = rules.get("account_policies", {}).get(account_code)
        if not account_policy:
            errors.append(f"active account {account_code!r} has no editorial policy")
            continue
        account_mode = account_policy.get("link_mode")
        if (
            account_mode
            and account_mode not in {"per_post_type", "per_author_rewrite_mode"}
            and account_mode not in link_modes
        ):
            errors.append(
                f"active account {account_code!r} uses unknown link mode {account_mode!r}"
            )

    routing = rules.get("editorial_routing") or {}
    if routing.get("route_order") != ["james_luan", "anonymous_default"]:
        errors.append("editorial routing must check james_luan before anonymous_default")
    route_specs = routing.get("routes") or {}
    if not (route_specs.get("anonymous_default", {}).get("match") or {}).get("fallback"):
        errors.append("anonymous_default editorial route must be the fallback")
    for route_id, route_spec in route_specs.items():
        for key in ("guidance", "reference", "resource"):
            path_value = route_spec.get(key)
            if not path_value or not (resource_paths.ROOT / path_value).is_file():
                errors.append(f"editorial route {route_id!r} has invalid {key} path")

    disclosed_routes = {
        route_id: override
        for route_id, override in rules.get("editorial_routes", {}).items()
        if override.get("validation_mode") == "disclosed_author"
    }
    for author, override in disclosed_routes.items():
        if override.get("validation_mode") != "disclosed_author":
            errors.append(
                f"source-author override {author!r} must use validation_mode "
                "'disclosed_author'"
            )
            continue
        opening = override.get("identity_opening") or {}
        required_terms = {
            str(term).strip().casefold()
            for term in opening.get("required_terms", [])
            if str(term).strip()
        }
        if opening.get("scope") != "first_paragraph":
            errors.append(
                f"source-author override {author!r} identity opening must target "
                "the first_paragraph"
            )
        if not {"james", "cto", "zilliz"}.issubset(required_terms):
            errors.append(
                f"source-author override {author!r} identity opening must require "
                "James, CTO, and Zilliz"
            )
        if override.get("required_disclosure"):
            errors.append(
                f"source-author override {author!r} must disclose identity in the "
                "body opening, not append a disclosure block"
            )
        required_account = override.get("required_account_code")
        accounts = override.get("accounts") or {}
        if required_account != "R3" or set(accounts) != {"R3"}:
            errors.append(
                f"source-author override {author!r} must route only through R3"
            )
            continue
        r3_override = accounts["R3"]
        expected_modes = {
            "r3_coherent_chapter_rewrite",
            "r3_article_summary_share",
        }
        if set(r3_override.get("allowed_rewrite_modes") or []) != expected_modes:
            errors.append(
                f"source-author override {author!r}/R3 must expose exactly the "
                f"configured chapter-series and article-summary modes"
            )
        modes = r3_override.get("modes") or {}
        if set(modes) != expected_modes:
            errors.append(
                f"source-author override {author!r}/R3 mode definitions are incomplete"
            )
        for mode_id, mode in modes.items():
            if mode.get("link_policy") not in link_modes:
                errors.append(
                    f"source-author override {author!r}/R3/{mode_id} uses an "
                    "unknown link policy"
                )
            if not (mode.get("style_contract") or {}).get("voice"):
                errors.append(
                    f"source-author override {author!r}/R3/{mode_id} must define "
                    "a style_contract voice"
                )
            if not mode.get("required_narrative_sequence"):
                errors.append(
                    f"source-author override {author!r}/R3/{mode_id} must define "
                    "a narrative sequence"
                )
        summary_share = modes.get("r3_article_summary_share") or {}
        chapter = modes.get("r3_coherent_chapter_rewrite") or {}
        if chapter.get("required_partn_pattern") != "^part[1-9][0-9]*$":
            errors.append(
                f"source-author override {author!r}/R3 chapter mode must require "
                "partn values part1, part2, and so on"
            )
        if chapter.get("link_policy") != "no_link":
            errors.append(
                f"source-author override {author!r}/R3 chapter mode must keep "
                "the Reddit body link-free"
            )
        if chapter.get("repeat_policy") != "may_repeat_until_full_source_covered":
            errors.append(
                f"source-author override {author!r}/R3 chapter mode must continue "
                "until the whole source is covered"
            )
        if summary_share.get("required_inline_link") != "source_url":
            errors.append(
                f"source-author override {author!r}/R3 article-summary mode must "
                "require source_url directly in the body"
            )
        if int(summary_share.get("max_rewrites_per_source_url") or 0) != 1:
            errors.append(
                f"source-author override {author!r}/R3 article-summary mode must "
                "allow exactly one rewrite per source_url"
            )

    source_field_policy = rules.get("original_source_field_policy") or {}
    if source_field_policy.get("scope") != "all_future_reddit_review_rows":
        errors.append("original_source_field_policy must cover every future review row")
    if source_field_policy.get("required_feishu_field") != "原文":
        errors.append("original_source_field_policy must write the Feishu 原文 field")
    if source_field_policy.get("field_value") != "source_url":
        errors.append("original_source_field_policy must map source_url to 原文")

    james_weekly = rules.get("james_weekly_mode_policy") or {}
    if james_weekly.get("enabled"):
        if int(james_weekly.get("james_post_count") or 0) != 3:
            errors.append("james_weekly_mode_policy james_post_count must be 3")
        if int(james_weekly.get("article_summary_share_count") or 0) != 1:
            errors.append("james_weekly_mode_policy article_summary_share_count must be 1")
        if james_weekly.get("article_summary_share_mode") != "r3_article_summary_share":
            errors.append("james_weekly_mode_policy must use r3_article_summary_share")

    if errors:
        raise ValueError("Invalid merged Reddit workflow/guidance contract: " + "; ".join(errors))


def r2_short_question_policy(rules=None):
    rules = rules or load_rules()
    return rules.get("r2_short_question_policy") or {}


def source_author_override(source_author, rules=None):
    rules = rules or load_rules()
    normalized = str(source_author or "").strip().casefold()
    routing = rules.get("editorial_routing") or {}
    for route_id in routing.get("route_order", []):
        route = (routing.get("routes") or {}).get(route_id, {})
        expected = (route.get("match") or {}).get(
            "source_author_exact_case_insensitive"
        )
        if expected and normalized == expected.strip().casefold():
            return (rules.get("editorial_routes") or {}).get(route_id, {})
    return {}


def editorial_route_id(source_author, rules=None):
    rules = rules or load_rules()
    normalized = str(source_author or "").strip().casefold()
    routing = rules.get("editorial_routing") or {}
    for route_id in routing.get("route_order", []):
        match = ((routing.get("routes") or {}).get(route_id, {}).get("match") or {})
        expected = match.get("source_author_exact_case_insensitive")
        if expected and normalized == expected.strip().casefold():
            return route_id
        if match.get("fallback"):
            return route_id
    raise ValueError("No editorial route matched source_author")


def source_author_account_override(
    source_author, account_code, rules=None, author_rewrite_mode=""
):
    override = source_author_override(source_author, rules)
    account_override = (override.get("accounts") or {}).get(account_code, {})
    modes = account_override.get("modes") or {}
    if author_rewrite_mode in modes:
        return {**account_override, **modes[author_rewrite_mode]}
    return account_override


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
        if account_code in (slot.get("allowed_accounts") or [slot.get("account_code")])
    }


def allowed_accounts_for_subreddit(subreddit, rules=None):
    slot = slot_for(subreddit, rules)
    if not slot:
        return set()
    return set(slot.get("allowed_accounts") or [slot.get("account_code")])


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
