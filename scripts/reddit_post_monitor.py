#!/usr/bin/env python3
"""Core helpers for read-only Reddit JSON monitoring and Feishu patches."""
import copy
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


POST_STATUS_OPTIONS = [
    "Active",
    "Removed",
    "Deleted",
    "Locked",
    "Archived",
    "Unavailable",
]
ALERT_OPTIONS = ["None", "Watch", "Alert"]
MILVUS_SIGNAL_OPTIONS = [
    "Milvus Mention",
    "Milvus Question",
    "Milvus Positive",
    "Milvus Negative",
    "Milvus Comparison",
    "Migration/Adoption",
    "Zilliz Mention",
]

MONITOR_FIELD_DEFS = [
    {"field_name": "Reddit JSON URL", "type": 15},
    {"field_name": "Upvotes", "type": 2, "property": {"formatter": "0"}},
    {"field_name": "Comments", "type": 2, "property": {"formatter": "0"}},
    {"field_name": "Downvotes (Estimated)", "type": 2, "property": {"formatter": "0"}},
    {"field_name": "Upvote Ratio", "type": 2, "property": {"formatter": "0.00%"}},
    {
        "field_name": "Reddit Post Status",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(POST_STATUS_OPTIONS)
            ]
        },
    },
    {"field_name": "Comment Summary", "type": 1},
    {
        "field_name": "Public Opinion Alert",
        "type": 3,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(ALERT_OPTIONS)
            ]
        },
    },
    {
        "field_name": "Milvus Signal",
        "type": 4,
        "property": {
            "options": [
                {"name": name, "color": index % 14}
                for index, name in enumerate(MILVUS_SIGNAL_OPTIONS)
            ]
        },
    },
    {
        "field_name": "Reddit Metrics Updated At",
        "type": 5,
        "property": {"date_formatter": "yyyy/MM/dd HH:mm"},
    },
]

POSITIVE_TERMS = [
    "good",
    "great",
    "useful",
    "helpful",
    "works well",
    "impressive",
    "interesting",
    "love",
    "solid",
    "fast",
    "accurate",
    "better",
]
NEGATIVE_TERMS = [
    "bad",
    "poor",
    "slow",
    "expensive",
    "difficult",
    "issue",
    "problem",
    "concern",
    "risk",
    "bug",
    "error",
    "failed",
    "failing",
    "worse",
    "not good",
    "doesn't work",
    "does not work",
    "not working",
]
STRONG_NEGATIVE_TERMS = [
    "broken",
    "useless",
    "misleading",
    "spam",
    "scam",
    "terrible",
    "hate",
    "avoid this",
    "marketing post",
    "advertisement",
]
COMPARISON_TERMS = [
    " vs ",
    "versus",
    "compare",
    "comparison",
    "alternative",
    "pinecone",
    "weaviate",
    "qdrant",
    "pgvector",
]
ADOPTION_TERMS = [
    "use milvus",
    "using milvus",
    "try milvus",
    "adopt milvus",
    "migrate",
    "migration",
    "deploy milvus",
    "production",
    "self-host",
]
QUESTION_TERMS = ["how", "what", "why", "when", "which", "anyone", "does", "can"]

THEME_TERMS = {
    "RAG/retrieval": ["rag", "retrieval", "rerank", "chunk"],
    "indexing/search": ["index", "search", "bm25", "hybrid"],
    "performance/scale": ["latency", "performance", "scale", "memory", "throughput"],
    "cost/operations": ["cost", "expensive", "deploy", "production", "kubernetes"],
    "local models": ["local model", "llama", "ollama", "quantization", "vram"],
    "vector databases": ["vector database", "vectordb", "milvus", "pgvector", "qdrant", "weaviate", "pinecone"],
}


class RedditFetchError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def monitor_field_defs():
    return copy.deepcopy(MONITOR_FIELD_DEFS)


def normalize_text(value):
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def sanitize_comment_text(value):
    text = normalize_text(value)
    text = re.sub(r"https?://\S+", "[link]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\w)/?u/[A-Za-z0-9_-]+", "[user]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\w)@[A-Za-z0-9_]{2,}", "[user]", text)
    return text


def _validate_reddit_url(url):
    raw = str(url or "").strip()
    if not raw:
        raise ValueError("Reddit Publish URL is empty")
    parsed = urllib.parse.urlsplit(raw)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Reddit URL must use HTTPS: {raw}")
    if not (host == "redd.it" or host == "reddit.com" or host.endswith(".reddit.com")):
        raise ValueError(f"Not a Reddit URL: {raw}")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError(f"Reddit URL must not contain credentials or a custom port: {raw}")
    return raw, parsed, host


def reddit_post_id(url):
    _, parsed, _ = _validate_reddit_url(url)
    match = re.search(r"(?:^|/)comments/([a-z0-9]+)(?:/|$)", parsed.path, re.IGNORECASE)
    if not match:
        raise ValueError(f"Reddit URL is not a canonical submission URL: {url}")
    return match.group(1).lower()


def normalize_reddit_json_url(url, limit=500):
    raw, parsed, _ = _validate_reddit_url(url)
    reddit_post_id(raw)
    path = parsed.path.rstrip("/")
    if not path.endswith(".json"):
        path += ".json"
    query = urllib.parse.urlencode({"raw_json": 1, "limit": max(1, int(limit)), "sort": "top"})
    return urllib.parse.urlunsplit(("https", parsed.netloc, path, query, ""))


def resolve_reddit_permalink(url, user_agent, timeout=30):
    raw, parsed, host = _validate_reddit_url(url)
    is_share_link = bool(re.search(r"/r/[^/]+/s/[^/]+/?$", parsed.path, re.IGNORECASE))
    if host != "redd.it" and not is_share_link:
        reddit_post_id(raw)
        return raw
    request = urllib.request.Request(
        raw,
        headers={"User-Agent": user_agent},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            resolved = response.geturl()
    except urllib.error.HTTPError as exc:
        raise RedditFetchError(exc.code, f"Reddit share URL returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RedditFetchError(None, f"Reddit share URL resolution failed: {exc.reason}") from exc
    try:
        _, resolved_parsed, _ = _validate_reddit_url(resolved)
        reddit_post_id(resolved)
    except ValueError as exc:
        raise RedditFetchError(None, f"Reddit share URL did not resolve to a submission: {resolved}") from exc
    return urllib.parse.urlunsplit(("https", resolved_parsed.netloc, resolved_parsed.path, "", ""))


def fetch_reddit_json(json_url, user_agent, timeout=30):
    request = urllib.request.Request(
        json_url,
        headers={
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RedditFetchError(
                    getattr(response, "status", 200),
                    "Reddit endpoint returned non-JSON content; resolve share links before adding .json",
                ) from exc
    except urllib.error.HTTPError as exc:
        raise RedditFetchError(exc.code, f"Reddit JSON returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RedditFetchError(None, f"Reddit JSON request failed: {exc.reason}") from exc


def _children(listing):
    if not isinstance(listing, dict):
        return []
    return (listing.get("data") or {}).get("children") or []


def flatten_comments(children, limit=500):
    comments = []

    def visit(nodes, depth=0):
        for child in nodes or []:
            if len(comments) >= limit:
                return
            if child.get("kind") != "t1":
                continue
            data = child.get("data") or {}
            body = sanitize_comment_text(data.get("body"))
            if body and body not in {"[deleted]", "[removed]"}:
                comments.append({
                    "body": body,
                    "score": int(data.get("score") or 0),
                    "depth": int(data.get("depth") or depth),
                })
            replies = data.get("replies")
            if isinstance(replies, dict):
                visit(_children(replies), depth + 1)

    visit(children)
    return comments


def detect_post_status(post):
    selftext = normalize_text(post.get("selftext")).lower()
    removed_by = normalize_text(post.get("removed_by_category")).lower()
    if removed_by == "deleted" or selftext == "[deleted]":
        return "Deleted"
    if removed_by or selftext == "[removed]":
        return "Removed"
    if post.get("locked"):
        return "Locked"
    if post.get("archived"):
        return "Archived"
    return "Active"


def estimate_downvotes(score, upvote_ratio):
    try:
        score = float(score)
        ratio = float(upvote_ratio)
    except (TypeError, ValueError):
        return None
    if ratio >= 1:
        return 0
    denominator = 2 * ratio - 1
    if score <= 0 or denominator <= 0:
        return None
    total_votes = score / denominator
    return max(0, int(round(total_votes * (1 - ratio))))


def _matches(text, terms):
    lowered = f" {text.lower()} "
    return [term for term in terms if term in lowered]


def _comment_sentiment(body):
    positive = len(_matches(body, POSITIVE_TERMS))
    negative = len(_matches(body, NEGATIVE_TERMS))
    strong_negative = len(_matches(body, STRONG_NEGATIVE_TERMS))
    if strong_negative or negative > positive:
        return "negative", bool(strong_negative)
    if positive > negative:
        return "positive", False
    return "neutral", False


def _truncate(text, limit=150):
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def analyze_comments(comments, sample_count=12):
    substantive = [comment for comment in comments if len(comment.get("body", "")) >= 8]
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    strong_negative = []
    theme_counts = {label: 0 for label in THEME_TERMS}
    milvus_comments = []

    for comment in substantive:
        body = comment["body"]
        sentiment, is_strong = _comment_sentiment(body)
        sentiment_counts[sentiment] += 1
        if is_strong:
            strong_negative.append(comment)
        lowered = body.lower()
        for label, terms in THEME_TERMS.items():
            if any(term in lowered for term in terms):
                theme_counts[label] += 1
        if "milvus" in lowered or "zilliz" in lowered:
            milvus_comments.append((comment, sentiment))

    total = len(substantive)
    negative_count = sentiment_counts["negative"]
    negative_ratio = (negative_count / total) if total else 0
    highest_strong_score = max((comment.get("score", 0) for comment in strong_negative), default=0)
    if len(strong_negative) >= 2 or (strong_negative and negative_ratio >= 0.4 and highest_strong_score >= 2):
        alert = "Alert"
    elif strong_negative or (negative_count >= 2 and negative_ratio >= 0.3):
        alert = "Watch"
    else:
        alert = "None"

    signals = []
    if milvus_comments:
        combined = " ".join(comment["body"].lower() for comment, _ in milvus_comments)
        if "milvus" in combined:
            signals.append("Milvus Mention")
        if "zilliz" in combined:
            signals.append("Zilliz Mention")
        if any("?" in comment["body"] or _matches(comment["body"], QUESTION_TERMS) for comment, _ in milvus_comments):
            signals.append("Milvus Question")
        if any(sentiment == "positive" for _, sentiment in milvus_comments):
            signals.append("Milvus Positive")
        if any(sentiment == "negative" for _, sentiment in milvus_comments):
            signals.append("Milvus Negative")
        if _matches(combined, COMPARISON_TERMS):
            signals.append("Milvus Comparison")
        if _matches(combined, ADOPTION_TERMS):
            signals.append("Migration/Adoption")

    ranked_themes = [
        label
        for label, count in sorted(theme_counts.items(), key=lambda item: (-item[1], item[0]))
        if count
    ][:3]
    top_comments = sorted(substantive, key=lambda comment: (-comment.get("score", 0), comment["body"]))
    if not total:
        summary = "Reddit JSON 中没有可用于归纳的有效评论。"
    else:
        theme_text = "、".join(ranked_themes) if ranked_themes else "没有重复出现的技术主题"
        summary = (
            f"共 {total} 条有效评论。主要主题：{theme_text}。"
            f"情绪信号：正面 {sentiment_counts['positive']} 条，"
            f"负面 {sentiment_counts['negative']} 条，中性 {sentiment_counts['neutral']} 条。"
        )
        if milvus_comments:
            summary += f" 其中 {len(milvus_comments)} 条提到 Milvus 或 Zilliz。"

    return {
        "comment_summary": summary,
        "public_opinion_alert": alert,
        "milvus_signal": signals,
        "sentiment_counts": sentiment_counts,
        "alert_basis": {
            "substantive_comments": total,
            "strong_negative_comments": len(strong_negative),
            "negative_ratio": round(negative_ratio, 3),
        },
        "comments_sample": [
            {"score": comment.get("score", 0), "body": _truncate(comment["body"], 500)}
            for comment in top_comments[: max(0, int(sample_count))]
        ],
    }


def parse_reddit_payload(payload, publish_url, json_url, max_comments=500, sample_count=12):
    if not isinstance(payload, list) or not payload:
        raise ValueError("Unexpected Reddit JSON shape: expected a listing array")
    post_children = _children(payload[0])
    if not post_children:
        raise ValueError("Reddit JSON did not include a submission")
    post = post_children[0].get("data") or {}
    comment_children = _children(payload[1]) if len(payload) > 1 else []
    comments = flatten_comments(comment_children, max_comments)
    analysis = analyze_comments(comments, sample_count=sample_count)
    score = post.get("score")
    upvote_ratio = post.get("upvote_ratio")
    return {
        "publish_url": publish_url,
        "reddit_json_url": json_url,
        "post_title": normalize_text(post.get("title")),
        "post_status": detect_post_status(post),
        "metrics": {
            "upvotes": int(post.get("ups") or 0),
            "comments": int(post.get("num_comments") or 0),
            "score": int(score or 0),
            "upvote_ratio": float(upvote_ratio) if upvote_ratio is not None else None,
            "estimated_downvotes": estimate_downvotes(score, upvote_ratio),
            "comments_retrieved": len(comments),
        },
        "comment_analysis": analysis,
    }


def unavailable_report(publish_url, json_url, status=404):
    return {
        "publish_url": publish_url,
        "reddit_json_url": json_url,
        "post_title": "",
        "post_status": "Unavailable",
        "metrics": {
            "upvotes": None,
            "comments": None,
            "score": None,
            "upvote_ratio": None,
            "estimated_downvotes": None,
            "comments_retrieved": 0,
        },
        "comment_analysis": {
            "comment_summary": f"Reddit JSON 端点返回 HTTP {status}，本次无法读取评论。",
            "public_opinion_alert": "None",
            "milvus_signal": [],
            "sentiment_counts": {"positive": 0, "negative": 0, "neutral": 0},
            "alert_basis": {"http_status": status},
            "comments_sample": [],
        },
    }


def apply_analysis_override(report, override):
    if not override:
        return report
    analysis = report["comment_analysis"]
    if "comment_summary" in override:
        summary = sanitize_comment_text(override["comment_summary"])
        if not summary:
            raise ValueError("comment_summary override must not be empty")
        analysis["comment_summary"] = summary
    if "public_opinion_alert" in override:
        alert = override["public_opinion_alert"]
        if alert not in ALERT_OPTIONS:
            raise ValueError(f"public_opinion_alert must be one of {ALERT_OPTIONS}")
        analysis["public_opinion_alert"] = alert
    if "milvus_signal" in override:
        signals = override["milvus_signal"] or []
        if not isinstance(signals, list):
            raise ValueError("milvus_signal override must be a list")
        invalid = sorted(set(signals) - set(MILVUS_SIGNAL_OPTIONS))
        if invalid:
            raise ValueError(f"unknown Milvus Signal values: {invalid}")
        analysis["milvus_signal"] = list(dict.fromkeys(signals))
    return report


def as_url_field(url):
    return {"link": url, "text": url}


def build_feishu_patch(report, updated_at=None):
    metrics = report.get("metrics") or {}
    analysis = report.get("comment_analysis") or {}
    timestamp = updated_at or datetime.now(timezone.utc)
    fields = {
        "Reddit JSON URL": as_url_field(report["reddit_json_url"]),
        "Reddit Post Status": report["post_status"],
        "Comment Summary": analysis.get("comment_summary", ""),
        "Public Opinion Alert": analysis.get("public_opinion_alert", "None"),
        "Milvus Signal": analysis.get("milvus_signal", []),
        "Reddit Metrics Updated At": int(timestamp.timestamp() * 1000),
    }
    metric_fields = {
        "Upvotes": metrics.get("upvotes"),
        "Comments": metrics.get("comments"),
        "Downvotes (Estimated)": metrics.get("estimated_downvotes"),
        "Upvote Ratio": metrics.get("upvote_ratio"),
    }
    fields.update({name: value for name, value in metric_fields.items() if value is not None})
    if report.get("post_status") in {"Removed", "Deleted"}:
        fields["Status"] = "Cancel"
    return fields
