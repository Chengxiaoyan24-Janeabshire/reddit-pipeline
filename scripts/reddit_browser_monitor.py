#!/usr/bin/env python3
"""Preview or write Chrome-visible Reddit monitoring observations to Feishu."""
import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import feishu_client


ROOT = Path(__file__).resolve().parents[1]
FIELD_MAP_PATH = ROOT / "config" / "feishu-fields.json"
SNAPSHOT_VERSION = 2
MONITOR_PRIORITY_DAYS = 7
MONITOR_MAX_AGE_DAYS = 14

BINARY_SIGNAL_OPTIONS = ["None", "Yes"]
QUESTION_SIGNAL_OPTIONS = BINARY_SIGNAL_OPTIONS
NEGATIVE_SIGNAL_OPTIONS = BINARY_SIGNAL_OPTIONS
DEBATE_SIGNAL_OPTIONS = BINARY_SIGNAL_OPTIONS
PRODUCT_SIGNAL_OPTIONS = BINARY_SIGNAL_OPTIONS
COMPETITOR_SIGNAL_OPTIONS = BINARY_SIGNAL_OPTIONS
MONITOR_STATUS_OPTIONS = ["Monitored", "Partial", "Unavailable"]
COMMENT_STANCE_OPTIONS = ["Positive", "Neutral", "Negative"]
COMMENT_SENTIMENT_OPTIONS = ["None", "Positive", "Mixed", "Neutral", "Negative"]

MONITOR_FIELD_DEFS = [
    {"field_name": "Upvotes", "type": 2, "property": {"formatter": "0"}},
    {"field_name": "Comments", "type": 2, "property": {"formatter": "0"}},
    {
        "field_name": "Impression (7 days)",
        "type": 2,
        "property": {"formatter": "0"},
    },
    {"field_name": "Comment Summary", "type": 1},
    {
        "field_name": "Comment Sentiment",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(COMMENT_SENTIMENT_OPTIONS)
            ]
        },
    },
    {
        "field_name": "Question Signal",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(QUESTION_SIGNAL_OPTIONS)
            ]
        },
    },
    {
        "field_name": "Negative Signal",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(NEGATIVE_SIGNAL_OPTIONS)
            ]
        },
    },
    {
        "field_name": "Debate Signal",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(DEBATE_SIGNAL_OPTIONS)
            ]
        },
    },
    {
        "field_name": "Product Signal",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(PRODUCT_SIGNAL_OPTIONS)
            ]
        },
    },
    {
        "field_name": "Competitor Signal",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(COMPETITOR_SIGNAL_OPTIONS)
            ]
        },
    },
    {"field_name": "Competitor Mentions", "type": 1},
    {
        "field_name": "Reddit Monitor Status",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(MONITOR_STATUS_OPTIONS)
            ]
        },
    },
    {"field_name": "Reddit Monitor Notes", "type": 1},
    {
        "field_name": "Reddit Metrics Updated At",
        "type": 5,
        "property": {"date_formatter": "yyyy/MM/dd HH:mm"},
    },
]

FORBIDDEN_OBSERVATION_KEYS = {
    "authors",
    "comment_authors",
    "comment_bodies",
    "comment_links",
    "comments_sample",
    "raw_comments",
    "reddit_json",
    "reddit_json_content",
    "usernames",
}
COMMENT_SENTIMENT_INPUT_KEYS = {
    "sentiment",
    "score",
    "score_approximate",
    "score_display",
    "top_1_percent_commenter",
}
HIDDEN_COMMENT_SCORE_DISPLAYS = {
    "-",
    "--",
    "—",
    "hidden",
    "score hidden",
    "vote",
    "votes",
    "n/a",
}
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
USERNAME_PATTERN = re.compile(
    r"(?<!\w)/?u/[A-Za-z0-9_-]+|(?<!\w)@[A-Za-z0-9_]{2,}",
    re.IGNORECASE,
)


def monitor_field_defs():
    return copy.deepcopy(MONITOR_FIELD_DEFS)


def load_field_map():
    if not FIELD_MAP_PATH.exists():
        return {}
    return json.loads(FIELD_MAP_PATH.read_text()).get("pipeline", {})


def canonicalize_reddit_url(value):
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlsplit(text)
    host = parsed.netloc.lower().split(":", 1)[0]
    if parsed.scheme.lower() != "https":
        return ""
    if host in {"reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com"}:
        host = "www.reddit.com"
        path = re.sub(r"/{2,}", "/", parsed.path)
        return urlunsplit(("https", host, path.rstrip("/") + "/", "", ""))
    if host == "redd.it" and parsed.path.strip("/"):
        return urlunsplit(("https", host, "/" + parsed.path.strip("/"), "", ""))
    return ""


def is_reddit_post_url(value):
    canonical = canonicalize_reddit_url(value)
    if not canonical:
        return False
    parsed = urlsplit(canonical)
    if parsed.netloc == "redd.it":
        return True
    return bool(
        re.search(r"/comments/[A-Za-z0-9]+(?:/|$)", parsed.path)
        or re.search(r"/r/[^/]+/s/[A-Za-z0-9]+(?:/|$)", parsed.path, re.IGNORECASE)
    )


def is_reddit_share_url(value):
    canonical = canonicalize_reddit_url(value)
    if not canonical:
        return False
    parsed = urlsplit(canonical)
    return bool(
        parsed.netloc == "www.reddit.com"
        and re.search(r"/r/[^/]+/s/[A-Za-z0-9]+(?:/|$)", parsed.path, re.IGNORECASE)
    )


def reddit_subreddit(value):
    canonical = canonicalize_reddit_url(value)
    if not canonical:
        return ""
    match = re.search(r"/r/([^/]+)(?:/|$)", urlsplit(canonical).path, re.IGNORECASE)
    return match.group(1).lower() if match else ""


def parse_visible_count(value):
    if value is None or isinstance(value, bool):
        return None, False
    if isinstance(value, int):
        return (value if value >= 0 else None), False
    if isinstance(value, float):
        return (int(round(value)) if value >= 0 else None), not value.is_integer()
    text = str(value).strip().lower().replace(",", "")
    if not text or text in {"-", "--", "—", "vote", "votes", "hidden", "n/a"}:
        return None, False
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([km]?)", text)
    if not match:
        return None, False
    number = float(match.group(1))
    suffix = match.group(2)
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000}[suffix]
    approximate = bool(suffix or not number.is_integer())
    return int(round(number * multiplier)), approximate


def parse_publish_datetime(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if abs(value) > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def monitor_window(publish_date, as_of=None):
    published_at = parse_publish_datetime(publish_date)
    now = (
        parse_publish_datetime(as_of) if as_of is not None else None
    ) or datetime.now().astimezone()
    if not published_at:
        return {
            "publish_date": "",
            "publish_date_ms": None,
            "age_days": None,
            "monitor_window": "missing_publish_date",
            "monitor_priority": None,
            "eligible": False,
        }
    local_tz = now.tzinfo or timezone.utc
    age_days = (
        now.astimezone(local_tz).date()
        - published_at.astimezone(local_tz).date()
    ).days
    if age_days < 0:
        window = "future_publish_date"
        priority = None
    elif age_days <= MONITOR_PRIORITY_DAYS:
        window = "within_7_days"
        priority = 1
    elif age_days <= MONITOR_MAX_AGE_DAYS:
        window = "days_8_to_14"
        priority = 2
    else:
        window = "outside_14_days"
        priority = None
    return {
        "publish_date": published_at.astimezone(timezone.utc).isoformat(),
        "publish_date_ms": int(published_at.timestamp() * 1000),
        "age_days": age_days,
        "monitor_window": window,
        "monitor_priority": priority,
        "eligible": priority is not None,
    }


def _target_priority_key(target):
    priority = target.get("monitor_priority")
    publish_date_ms = target.get("publish_date_ms")
    return (
        priority if isinstance(priority, int) else 99,
        -(publish_date_ms or 0),
        target.get("record_id", ""),
    )


def parse_visible_comment_score(value):
    if value is None or isinstance(value, bool):
        return None, False
    if isinstance(value, int):
        return value, False
    if isinstance(value, float):
        return int(round(value)), not value.is_integer()
    text = str(value).strip().lower().replace(",", "")
    if not text or text in HIDDEN_COMMENT_SCORE_DISPLAYS:
        return None, False
    text = re.sub(r"\s+(?:points?|votes?)$", "", text).strip()
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*([km]?)", text)
    if not match:
        return None, False
    number = float(match.group(1))
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000}[match.group(2)]
    approximate = bool(match.group(2) or not number.is_integer())
    return int(round(number * multiplier)), approximate


def _visible_vote_bonus(score):
    magnitude = abs(score or 0)
    if magnitude < 2:
        return 0.0
    if magnitude < 5:
        return 0.25
    if magnitude < 10:
        return 0.5
    if magnitude < 25:
        return 1.0
    if magnitude < 100:
        return 1.5
    return 2.0


def _validate_comment_sentiment_input(raw, index):
    if not isinstance(raw, dict):
        raise ValueError(f"comment_sentiments[{index}] must be an object")
    unexpected = sorted(set(raw) - COMMENT_SENTIMENT_INPUT_KEYS)
    if unexpected:
        raise ValueError(
            f"comment_sentiments[{index}] contains unsupported fields: {unexpected}"
        )
    sentiment = _clean_text(raw.get("sentiment"))
    if sentiment not in COMMENT_STANCE_OPTIONS:
        raise ValueError(
            f"comment_sentiments[{index}].sentiment must be one of "
            f"{COMMENT_STANCE_OPTIONS}"
        )
    score_display = _clean_text(raw.get("score_display"))
    if not score_display:
        raise ValueError(
            f"comment_sentiments[{index}].score_display is required; use "
            "'Score hidden' when Reddit does not show it"
        )
    score_from_display, display_approximate = parse_visible_comment_score(
        score_display
    )
    if (
        score_from_display is None
        and score_display.lower() not in HIDDEN_COMMENT_SCORE_DISPLAYS
    ):
        raise ValueError(
            f"comment_sentiments[{index}].score_display is not a visible Reddit score"
        )
    score_from_value, value_approximate = parse_visible_comment_score(raw.get("score"))
    if raw.get("score") is not None and score_from_value != score_from_display:
        raise ValueError(
            f"comment_sentiments[{index}].score does not match score_display"
        )
    top_commenter = raw.get("top_1_percent_commenter", False)
    if not isinstance(top_commenter, bool):
        raise ValueError(
            f"comment_sentiments[{index}].top_1_percent_commenter must be boolean"
        )
    score_approximate = raw.get("score_approximate", False)
    if not isinstance(score_approximate, bool):
        raise ValueError(
            f"comment_sentiments[{index}].score_approximate must be boolean"
        )

    stance_value = {"Positive": 1.0, "Neutral": 0.0, "Negative": -1.0}[
        sentiment
    ]
    vote_bonus = _visible_vote_bonus(score_from_display)
    vote_direction = -1.0 if (score_from_display or 0) < 0 else 1.0
    vote_contribution = stance_value * vote_direction * vote_bonus
    top_commenter_contribution = stance_value * (0.5 if top_commenter else 0.0)
    contribution = stance_value + vote_contribution + top_commenter_contribution
    weight_mass = abs(stance_value) * (
        1.0 + vote_bonus + (0.5 if top_commenter else 0.0)
    )
    return {
        "sentiment": sentiment,
        "score_display": score_display,
        "score": score_from_display,
        "score_approximate": bool(
            score_approximate or display_approximate or value_approximate
        ),
        "top_1_percent_commenter": top_commenter,
        "vote_weight": vote_bonus,
        "weighted_contribution": round(contribution, 4),
        "weight_mass": round(weight_mass, 4),
    }


def calculate_comment_sentiment(comment_sentiments, comments_reviewed):
    if not comment_sentiments:
        return {
            "label": "None" if comments_reviewed == 0 else "Neutral",
            "score": None if comments_reviewed == 0 else 0.0,
            "positive_comments": 0,
            "neutral_comments": comments_reviewed,
            "negative_comments": 0,
            "visible_scored_comments": 0,
            "approximate_or_hidden_scores": 0,
            "top_1_percent_comments": 0,
        }
    total_contribution = sum(
        row["weighted_contribution"] for row in comment_sentiments
    )
    total_mass = sum(row["weight_mass"] for row in comment_sentiments)
    score = round(total_contribution / total_mass, 4) if total_mass else 0.0
    non_neutral = any(row["sentiment"] != "Neutral" for row in comment_sentiments)
    if not non_neutral:
        label = "Neutral"
    elif score >= 0.15:
        label = "Positive"
    elif score <= -0.15:
        label = "Negative"
    else:
        label = "Mixed"
    return {
        "label": label,
        "score": score,
        "positive_comments": sum(
            row["sentiment"] == "Positive" for row in comment_sentiments
        ),
        "neutral_comments": sum(
            row["sentiment"] == "Neutral" for row in comment_sentiments
        ),
        "negative_comments": sum(
            row["sentiment"] == "Negative" for row in comment_sentiments
        ),
        "visible_scored_comments": sum(
            row["score"] is not None for row in comment_sentiments
        ),
        "approximate_or_hidden_scores": sum(
            row["score"] is None or row["score_approximate"]
            for row in comment_sentiments
        ),
        "top_1_percent_comments": sum(
            row["top_1_percent_commenter"] for row in comment_sentiments
        ),
    }


def load_feishu_targets(app_token, table_id, include_all_statuses=False, as_of=None):
    field_map = load_field_map()
    draft_id_field = field_map.get("draft_id", "Draft ID")
    status_field = field_map.get("status", "Status")
    publish_url_field = field_map.get("publish_url", "Publish URL")
    publish_date_field = field_map.get("publish_date", "Publish Date")
    targets = []
    for record in feishu_client.list_records(app_token, table_id):
        fields = record.get("fields", {})
        status = feishu_client.extract_text(fields.get(status_field))
        if not include_all_statuses and status != "Published":
            continue
        publish_url = feishu_client.extract_url(fields.get(publish_url_field))
        window = monitor_window(fields.get(publish_date_field), as_of=as_of)
        valid_url = is_reddit_post_url(publish_url)
        skip_reasons = []
        if not window["eligible"]:
            skip_reasons.append(window["monitor_window"])
        if not valid_url:
            skip_reasons.append("invalid_publish_url")
        targets.append(
            {
                "record_id": record.get("record_id", ""),
                "draft_id": feishu_client.extract_text(fields.get(draft_id_field)),
                "status": status,
                "publish_url": publish_url,
                "canonical_publish_url": canonicalize_reddit_url(publish_url),
                **window,
                "monitorable": bool(valid_url and window["eligible"]),
                "skip_reasons": skip_reasons,
            }
        )
    return sorted(targets, key=_target_priority_key)


def option_names(field):
    return {
        option.get("name")
        for option in (field.get("property") or {}).get("options", [])
        if option.get("name")
    }


def field_plan(existing_fields):
    by_name = {field.get("field_name"): field for field in existing_fields}
    missing = []
    incompatible = []
    options_missing = []
    for desired in monitor_field_defs():
        current = by_name.get(desired["field_name"])
        if not current:
            missing.append(desired)
            continue
        if current.get("type") != desired.get("type"):
            incompatible.append(
                {
                    "field": desired["field_name"],
                    "existing_type": current.get("type"),
                    "required_type": desired.get("type"),
                }
            )
            continue
        desired_options = option_names(desired)
        current_options = option_names(current)
        if desired_options and current_options != desired_options:
            options_missing.append(
                {
                    "field": desired["field_name"],
                    "existing": sorted(current_options),
                    "required": sorted(desired_options),
                }
            )
    return {
        "missing": missing,
        "incompatible": incompatible,
        "options_missing": options_missing,
    }


def ensure_monitor_fields(app_token, table_id, existing_fields, plan):
    if plan["incompatible"]:
        raise RuntimeError(
            f"Existing monitor fields have incompatible types: {plan['incompatible']}"
        )
    created = []
    updated = []
    by_name = {field.get("field_name"): field for field in existing_fields}
    for desired in plan["missing"]:
        feishu_client.create_field(app_token, table_id, desired)
        created.append(desired["field_name"])
    option_fields = {row["field"] for row in plan["options_missing"]}
    for desired in monitor_field_defs():
        if desired["field_name"] not in option_fields:
            continue
        current = by_name[desired["field_name"]]
        feishu_client.update_field(
            app_token,
            table_id,
            current["field_id"],
            desired,
        )
        updated.append(desired["field_name"])
    return created, updated


def compact_field_plan(plan):
    return {
        "missing": [field["field_name"] for field in plan.get("missing", [])],
        "incompatible": plan.get("incompatible", []),
        "options_missing": plan.get("options_missing", []),
    }


def comparable_targets(targets):
    return sorted(
        [
            {
                "record_id": target.get("record_id", ""),
                "draft_id": target.get("draft_id", ""),
                "status": target.get("status", ""),
                "publish_url": target.get("publish_url", ""),
                "canonical_publish_url": target.get("canonical_publish_url", ""),
                "publish_date": target.get("publish_date", ""),
                "publish_date_ms": target.get("publish_date_ms"),
                "monitor_window": target.get("monitor_window", ""),
                "monitor_priority": target.get("monitor_priority"),
                "monitorable": bool(target.get("monitorable")),
                "skip_reasons": list(target.get("skip_reasons") or []),
            }
            for target in targets
        ],
        key=lambda target: (target["record_id"], target["draft_id"]),
    )


def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _assert_no_comment_identity(text, field_name):
    if URL_PATTERN.search(text) or USERNAME_PATTERN.search(text):
        raise ValueError(
            f"{field_name} must not contain Reddit usernames, handles, or URLs"
        )


def validate_observation(raw, target):
    if not isinstance(raw, dict):
        raise ValueError("Each browser observation must be an object")
    if not target.get("monitorable"):
        raise ValueError("Observation target is outside the active 14-day monitor set")
    forbidden = sorted(FORBIDDEN_OBSERVATION_KEYS & set(raw))
    if forbidden:
        raise ValueError(
            f"Browser observations must not persist raw Reddit content fields: {forbidden}"
        )
    record_id = _clean_text(raw.get("record_id"))
    if not record_id or record_id != target.get("record_id"):
        raise ValueError("Observation record_id does not match a Feishu target")
    draft_id = _clean_text(raw.get("draft_id") or target.get("draft_id"))
    if target.get("draft_id") and draft_id != target.get("draft_id"):
        raise ValueError("Observation draft_id does not match the Feishu target")
    publish_url = _clean_text(raw.get("publish_url") or target.get("publish_url"))
    if canonicalize_reddit_url(publish_url) != target.get("canonical_publish_url"):
        raise ValueError("Observation publish_url does not match the Feishu target")
    canonical_url = canonicalize_reddit_url(raw.get("canonical_url") or publish_url)
    if is_reddit_share_url(target.get("publish_url")):
        if not is_reddit_post_url(canonical_url) or is_reddit_share_url(canonical_url):
            raise ValueError("Reddit share URL must resolve to a canonical post page")
        expected_subreddit = reddit_subreddit(target.get("publish_url"))
        observed_subreddit = reddit_subreddit(canonical_url)
        if expected_subreddit and observed_subreddit != expected_subreddit:
            raise ValueError(
                "Resolved Reddit post subreddit does not match the Feishu share URL"
            )
    elif canonical_url != target.get("canonical_publish_url"):
        raise ValueError("Observed Reddit page does not match the Feishu Publish URL")

    status = _clean_text(raw.get("monitor_status") or "")
    if status not in MONITOR_STATUS_OPTIONS:
        raise ValueError(f"monitor_status must be one of {MONITOR_STATUS_OPTIONS}")

    upvotes_display = _clean_text(raw.get("upvotes_display"))
    comments_display = _clean_text(raw.get("comments_display"))
    upvotes_from_display, upvotes_display_approximate = parse_visible_count(
        upvotes_display
    )
    comments_from_display, comments_display_approximate = parse_visible_count(
        comments_display
    )
    upvotes_from_value, upvotes_value_approximate = parse_visible_count(
        raw.get("upvotes")
    )
    comments_from_value, comments_value_approximate = parse_visible_count(
        raw.get("comments")
    )
    if (
        raw.get("upvotes") is not None
        and upvotes_display
        and upvotes_from_value != upvotes_from_display
    ):
        raise ValueError("upvotes does not match the visible upvotes_display")
    if (
        raw.get("comments") is not None
        and comments_display
        and comments_from_value != comments_from_display
    ):
        raise ValueError("comments does not match the visible comments_display")
    upvotes = upvotes_from_display if upvotes_display else upvotes_from_value
    comments = comments_from_display if comments_display else comments_from_value
    upvotes_approximate = bool(
        raw.get("upvotes_approximate", False)
        or upvotes_display_approximate
        or upvotes_value_approximate
    )
    comments_approximate = bool(
        raw.get("comments_approximate", False)
        or comments_display_approximate
        or comments_value_approximate
    )

    try:
        comments_reviewed = int(raw.get("comments_reviewed") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("comments_reviewed must be a non-negative integer") from exc
    if comments_reviewed < 0:
        raise ValueError("comments_reviewed must be a non-negative integer")

    raw_comment_sentiments = raw.get("comment_sentiments", [])
    if not isinstance(raw_comment_sentiments, list):
        raise ValueError("comment_sentiments must be a list")
    if len(raw_comment_sentiments) != comments_reviewed:
        raise ValueError(
            "comment_sentiments must contain one sanitized weighting input for "
            "every reviewed substantive comment"
        )
    comment_sentiments = [
        _validate_comment_sentiment_input(row, index)
        for index, row in enumerate(raw_comment_sentiments)
    ]
    sentiment_summary = calculate_comment_sentiment(
        comment_sentiments, comments_reviewed
    )
    supplied_sentiment = _clean_text(raw.get("comment_sentiment"))
    if supplied_sentiment and supplied_sentiment != sentiment_summary["label"]:
        raise ValueError(
            "comment_sentiment does not match the deterministic weighted result"
        )
    if raw.get("comment_sentiment_score") is not None:
        try:
            supplied_score = round(float(raw["comment_sentiment_score"]), 4)
        except (TypeError, ValueError) as exc:
            raise ValueError("comment_sentiment_score must be numeric") from exc
        if supplied_score != sentiment_summary["score"]:
            raise ValueError(
                "comment_sentiment_score does not match the deterministic weighted result"
            )

    question_signal = _clean_text(raw.get("question_signal") or "None")
    negative_signal = _clean_text(raw.get("negative_signal") or "None")
    debate_signal = _clean_text(raw.get("debate_signal") or "None")
    product_signal = _clean_text(raw.get("product_signal") or "None")
    competitor_signal = _clean_text(raw.get("competitor_signal") or "None")
    for field_name, value, options in [
        ("question_signal", question_signal, QUESTION_SIGNAL_OPTIONS),
        ("negative_signal", negative_signal, NEGATIVE_SIGNAL_OPTIONS),
        ("debate_signal", debate_signal, DEBATE_SIGNAL_OPTIONS),
        ("product_signal", product_signal, PRODUCT_SIGNAL_OPTIONS),
        ("competitor_signal", competitor_signal, COMPETITOR_SIGNAL_OPTIONS),
    ]:
        if value not in options:
            raise ValueError(f"{field_name} must be one of {options}")

    summary = _clean_text(raw.get("comment_summary"))
    notes = _clean_text(raw.get("monitor_notes"))
    competitor_mentions = _clean_text(raw.get("competitor_mentions"))
    _assert_no_comment_identity(summary, "comment_summary")
    _assert_no_comment_identity(notes, "monitor_notes")
    _assert_no_comment_identity(competitor_mentions, "competitor_mentions")

    if competitor_signal == "None" and competitor_mentions:
        raise ValueError(
            "competitor_mentions must be empty when competitor_signal=None"
        )
    if competitor_signal == "Yes" and not competitor_mentions:
        raise ValueError(
            "competitor_mentions is required when competitor_signal=Yes"
        )

    if status in {"Monitored", "Partial"} and not summary:
        raise ValueError("Monitored observations require comment_summary")
    if status in {"Monitored", "Partial"} and (
        not upvotes_display or not comments_display
    ):
        raise ValueError(
            "Monitored observations require visible upvotes_display and comments_display"
        )
    if status == "Partial" and not notes:
        raise ValueError("Partial observations require monitor_notes explaining coverage")
    if status == "Monitored":
        if upvotes is None or comments is None:
            raise ValueError(
                "Hidden or unreadable visible metrics require monitor_status=Partial"
            )
        if upvotes_approximate or comments_approximate:
            raise ValueError("Rounded visible metrics require monitor_status=Partial")
        if comments is not None and comments_reviewed < comments:
            raise ValueError(
                "A partial comment sample requires monitor_status=Partial"
            )
        if sentiment_summary["approximate_or_hidden_scores"]:
            raise ValueError(
                "Rounded or hidden visible comment scores require monitor_status=Partial"
            )
    if comments is not None and comments_reviewed > comments:
        raise ValueError("comments_reviewed cannot exceed the visible comment count")
    if status == "Unavailable" and not notes:
        raise ValueError("Unavailable observations require monitor_notes")
    if comments_reviewed == 0 and any(
        value != "None"
        for value in (
            question_signal,
            negative_signal,
            debate_signal,
            product_signal,
            competitor_signal,
        )
    ):
        raise ValueError("Comment signals require at least one reviewed comment")

    observed_at = _clean_text(raw.get("observed_at")) or datetime.now(
        timezone.utc
    ).isoformat()
    try:
        observed_datetime = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be an ISO-8601 timestamp") from exc
    if observed_datetime.tzinfo is None:
        observed_datetime = observed_datetime.replace(tzinfo=timezone.utc)

    return {
        "record_id": record_id,
        "draft_id": draft_id,
        "publish_url": publish_url,
        "canonical_url": canonical_url,
        "page_title": _clean_text(raw.get("page_title")),
        "observed_at": observed_datetime.astimezone(timezone.utc).isoformat(),
        "upvotes": upvotes,
        "upvotes_display": upvotes_display,
        "upvotes_approximate": upvotes_approximate,
        "comments": comments,
        "comments_display": comments_display,
        "comments_approximate": comments_approximate,
        "comments_reviewed": comments_reviewed,
        "comment_sentiments": comment_sentiments,
        "comment_sentiment": sentiment_summary["label"],
        "comment_sentiment_score": sentiment_summary["score"],
        "comment_sentiment_summary": sentiment_summary,
        "comment_summary": summary,
        "question_signal": question_signal,
        "negative_signal": negative_signal,
        "debate_signal": debate_signal,
        "product_signal": product_signal,
        "competitor_signal": competitor_signal,
        "competitor_mentions": competitor_mentions,
        "monitor_status": status,
        "monitor_notes": notes,
    }


def build_feishu_patch(observation):
    observed_at = datetime.fromisoformat(
        observation["observed_at"].replace("Z", "+00:00")
    )
    fields = {
        "Comment Summary": observation.get("comment_summary", ""),
        "Comment Sentiment": observation.get("comment_sentiment", "None"),
        "Question Signal": observation.get("question_signal", "None"),
        "Negative Signal": observation.get("negative_signal", "None"),
        "Debate Signal": observation.get("debate_signal", "None"),
        "Product Signal": observation.get("product_signal", "None"),
        "Competitor Signal": observation.get("competitor_signal", "None"),
        "Competitor Mentions": observation.get("competitor_mentions", ""),
        "Reddit Monitor Status": observation.get("monitor_status", "Unavailable"),
        "Reddit Monitor Notes": observation.get("monitor_notes", ""),
        "Reddit Metrics Updated At": int(observed_at.timestamp() * 1000),
    }
    if observation.get("upvotes") is not None:
        fields["Upvotes"] = observation["upvotes"]
    if observation.get("comments") is not None:
        fields["Comments"] = observation["comments"]
    return fields


def summarize_observations(observations):
    return {
        "monitor_status": {
            option: sum(row.get("monitor_status") == option for row in observations)
            for option in MONITOR_STATUS_OPTIONS
        },
        "question_signal": {
            option: sum(row.get("question_signal") == option for row in observations)
            for option in QUESTION_SIGNAL_OPTIONS
        },
        "negative_signal": {
            option: sum(row.get("negative_signal") == option for row in observations)
            for option in NEGATIVE_SIGNAL_OPTIONS
        },
        "debate_signal": {
            option: sum(row.get("debate_signal") == option for row in observations)
            for option in DEBATE_SIGNAL_OPTIONS
        },
        "product_signal": {
            option: sum(row.get("product_signal") == option for row in observations)
            for option in PRODUCT_SIGNAL_OPTIONS
        },
        "competitor_signal": {
            option: sum(row.get("competitor_signal") == option for row in observations)
            for option in COMPETITOR_SIGNAL_OPTIONS
        },
        "comment_sentiment": {
            option: sum(row.get("comment_sentiment") == option for row in observations)
            for option in COMMENT_SENTIMENT_OPTIONS
        },
        "top_1_percent_comments": sum(
            int((row.get("comment_sentiment_summary") or {}).get("top_1_percent_comments") or 0)
            for row in observations
        ),
        "comments_reviewed": sum(
            int(row.get("comments_reviewed") or 0) for row in observations
        ),
        "visible_comments": sum(
            int(row.get("comments") or 0) for row in observations
        ),
    }


def load_observations(path):
    payload = json.loads(Path(path).read_text())
    rows = payload.get("observations", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Observation file must contain observations[]")
    return rows


def _snapshot_digest(payload):
    body = dict(payload)
    body.pop("digest", None)
    serialized = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def build_snapshot(targets, observations, plan, include_all_statuses=False):
    snapshot = {
        "version": SNAPSHOT_VERSION,
        "source": "chrome_visible_reddit_page",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection": {
            "include_all_statuses": bool(include_all_statuses),
            "priority_days": MONITOR_PRIORITY_DAYS,
            "max_age_days": MONITOR_MAX_AGE_DAYS,
        },
        "targets": comparable_targets(targets),
        "field_plan": compact_field_plan(plan),
        "observations": observations,
    }
    snapshot["digest"] = _snapshot_digest(snapshot)
    return snapshot


def save_snapshot(path, snapshot):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    return str(destination)


def load_snapshot(path):
    snapshot = json.loads(Path(path).read_text())
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot must be a JSON object")
    if snapshot.get("version") != SNAPSHOT_VERSION:
        raise ValueError(f"Unsupported snapshot version: {snapshot.get('version')!r}")
    if snapshot.get("source") != "chrome_visible_reddit_page":
        raise ValueError("Live updates require a Chrome-visible Reddit preview snapshot")
    if not snapshot.get("digest") or snapshot["digest"] != _snapshot_digest(snapshot):
        raise ValueError("Snapshot digest mismatch; run a new browser preview")
    if not isinstance(snapshot.get("observations"), list):
        raise ValueError("Snapshot observations must be a list")
    return snapshot


def validate_snapshot(snapshot, targets, plan, include_all_statuses=False):
    expected_selection = {
        "include_all_statuses": bool(include_all_statuses),
        "priority_days": MONITOR_PRIORITY_DAYS,
        "max_age_days": MONITOR_MAX_AGE_DAYS,
    }
    if snapshot.get("selection") != expected_selection:
        raise ValueError("Snapshot selection does not match the current command")
    if snapshot.get("targets") != comparable_targets(targets):
        raise ValueError(
            "Feishu target rows, Publish URLs, Publish Dates, or monitoring windows "
            "changed after preview; run a new browser preview"
        )
    if snapshot.get("field_plan") != compact_field_plan(plan):
        raise ValueError(
            "Feishu monitor field plan changed after preview; run a new browser preview"
        )
    target_ids = {target.get("record_id") for target in targets}
    observed_ids = [row.get("record_id") for row in snapshot["observations"]]
    if len(observed_ids) != len(set(observed_ids)) or any(
        record_id not in target_ids for record_id in observed_ids
    ):
        raise ValueError("Snapshot observations do not match previewed Feishu records")
    return snapshot["observations"]


def summarize_target_windows(targets):
    return {
        window: sum(target.get("monitor_window") == window for target in targets)
        for window in (
            "within_7_days",
            "days_8_to_14",
            "outside_14_days",
            "missing_publish_date",
            "future_publish_date",
        )
    }


def _table_config():
    table_ids = feishu_client.get_table_ids()
    app_token = table_ids.get("reddit_bitable_app_token") or table_ids.get(
        "bitable_app_token"
    )
    table_id = table_ids.get("reddit_persona_pipeline_table_id")
    if not app_token or not table_id:
        raise RuntimeError("Missing Reddit Persona Pipeline app/table configuration")
    return app_token, table_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-targets", action="store_true")
    parser.add_argument("--observations-file")
    parser.add_argument("--snapshot-out")
    parser.add_argument("--snapshot-in")
    parser.add_argument("--ensure-fields", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.write and not args.snapshot_in:
        parser.error("--write requires --snapshot-in from a reviewed browser preview")
    if args.ensure_fields and not args.write:
        parser.error("--ensure-fields is allowed only with --write")
    if args.snapshot_out and (args.snapshot_in or args.write):
        parser.error("--snapshot-out cannot be combined with --snapshot-in or --write")
    if args.observations_file and args.snapshot_in:
        parser.error("--snapshot-in already contains reviewed observations")
    if not args.list_targets and not args.snapshot_in and not args.observations_file:
        parser.error("provide --list-targets, --observations-file, or --snapshot-in")

    app_token, table_id = _table_config()
    targets = load_feishu_targets(app_token, table_id)
    monitorable = [target for target in targets if target.get("monitorable")]
    skipped = [target for target in targets if not target.get("monitorable")]

    if args.list_targets:
        print(
            json.dumps(
                {
                    "ok": True,
                    "source": "feishu_publish_url",
                    "targets": monitorable,
                    "skipped": skipped,
                    "target_windows": summarize_target_windows(targets),
                    "monitoring_order": ["within_7_days", "days_8_to_14"],
                    "max_age_days": MONITOR_MAX_AGE_DAYS,
                    "browser_requirement": "Read visible Reddit page content through Chrome/Browser only; do not use Reddit JSON or network-response inspection.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    existing_fields = feishu_client.list_fields(app_token, table_id)
    plan = field_plan(existing_fields)
    errors = []
    observations = []
    snapshot_written = ""
    fields_created = []
    fields_updated = []
    records_updated = []

    if args.snapshot_in:
        try:
            snapshot = load_snapshot(args.snapshot_in)
            observations = validate_snapshot(
                snapshot,
                targets,
                plan,
            )
        except Exception as exc:
            errors.append({"stage": "snapshot_validation", "error": str(exc)})
    else:
        by_id = {target["record_id"]: target for target in monitorable}
        try:
            raw_observations = load_observations(args.observations_file)
        except Exception as exc:
            raw_observations = []
            errors.append({"stage": "observation_load", "error": str(exc)})
        seen = set()
        for raw in raw_observations:
            record_id = _clean_text(raw.get("record_id")) if isinstance(raw, dict) else ""
            target = by_id.get(record_id)
            if not target:
                errors.append(
                    {
                        "record_id": record_id,
                        "error": "Observation does not match a monitorable Feishu target",
                    }
                )
                continue
            if record_id in seen:
                errors.append({"record_id": record_id, "error": "Duplicate observation"})
                continue
            seen.add(record_id)
            try:
                observation = validate_observation(raw, target)
                observation["feishu_patch"] = build_feishu_patch(observation)
                observations.append(observation)
            except Exception as exc:
                errors.append({"record_id": record_id, "error": str(exc)})

        if args.snapshot_out and not errors:
            if plan["incompatible"]:
                errors.append(
                    {
                        "stage": "snapshot_validation",
                        "error": f"Monitor field types conflict: {plan['incompatible']}",
                    }
                )
            else:
                snapshot_written = save_snapshot(
                    args.snapshot_out,
                    build_snapshot(
                        targets,
                        observations,
                        plan,
                    ),
                )

    write_blocked = bool(errors)
    if args.write and not write_blocked:
        if plan["incompatible"]:
            errors.append(
                {
                    "stage": "field_validation",
                    "error": f"Monitor field types conflict: {plan['incompatible']}",
                }
            )
        if (plan["missing"] or plan["options_missing"]) and not args.ensure_fields:
            errors.append(
                {
                    "stage": "field_validation",
                    "error": "Monitor fields are missing; rerun the approved snapshot with --ensure-fields --write",
                }
            )
        write_blocked = bool(errors)
        if not write_blocked:
            try:
                if args.ensure_fields:
                    fields_created, fields_updated = ensure_monitor_fields(
                        app_token, table_id, existing_fields, plan
                    )
                for observation in observations:
                    feishu_client.update_record(
                        app_token,
                        table_id,
                        observation["record_id"],
                        observation["feishu_patch"],
                    )
                    records_updated.append(observation["record_id"])
            except Exception as exc:
                errors.append({"stage": "feishu_write", "error": str(exc)})
                write_blocked = True

    output = {
        "ok": not errors,
        "source": "chrome_visible_reddit_page",
        "targets": len(targets),
        "monitorable": len(monitorable),
        "target_windows": summarize_target_windows(targets),
        "monitoring_order": ["within_7_days", "days_8_to_14"],
        "max_age_days": MONITOR_MAX_AGE_DAYS,
        "observed": len(observations),
        "observation_summary": summarize_observations(observations),
        "skipped": skipped,
        "observations": observations,
        "errors": errors,
        "write_requested": args.write,
        "write_blocked": write_blocked,
        "field_plan": compact_field_plan(plan),
        "fields_created": fields_created,
        "fields_updated": fields_updated,
        "records_updated": records_updated,
        "snapshot_used": args.snapshot_in or "",
        "snapshot_written": snapshot_written,
        "browser_note": "Metrics and comment signals come only from visible Chrome/Browser page state; no Reddit JSON or API response is used.",
        "coverage_note": "Rounded or partially loaded metrics, comment scores, or comment coverage must be marked Partial and explained in Reddit Monitor Notes.",
        "sentiment_note": "Comment Sentiment is computed from sanitized per-comment stance, visible net score, and visible Top 1% Commenter badge inputs; hidden votes are never inferred.",
        "impressions_note": "Impression (7 days) is retained as a separate backend-populated field and is never overwritten by browser monitoring.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
