#!/usr/bin/env python3
"""Screen Reddit blog candidates for the fixed R1/R2 weekly lanes.

This mirrors the Medium pipeline's pre-screen + persona classification pattern,
but adapted for Reddit:
  - reject/borderline weak marketing or thin posts;
  - score technical fit against the active R1/R2 account lanes;
  - select only the fitting account(s), without forcing both;
  - recommend fixed subreddit and post-type combinations.

Output is JSON on stdout. Feishu pool screening is handled by
`screen_feishu_pool.py`.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import weekly_post_rules

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "account_topic_rules.json"
TOPICS = ROOT / "data" / "topic_bank.json"
FETCH = ROOT / "scripts" / "fetch_blog.py"
VENV_PY = ROOT / ".venv" / "bin" / "python3"

REJECT_SIGNALS = {
    "press_release": [
        "press release",
        "named a leader",
        "award",
        "funding",
        "partnership",
        "joins forces",
        "announces partnership",
        "recognized by",
        "trusted by thousands",
    ],
    "campaign": [
        "book a demo",
        "sign up",
        "contact sales",
        "fully managed experience",
        "game changer",
        "seamlessly",
        "unlock the power",
    ],
}

POSITIVE_SIGNALS = [
    "agent",
    "agents",
    "ai data infra",
    "benchmark",
    "vdbbench",
    "latency",
    "recall",
    "precision",
    "architecture",
    "database",
    "vector",
    "vector database",
    "storage engine",
    "lakebase",
    "index",
    "hnsw",
    "ivf",
    "diskann",
    "rag",
    "retrieval",
    "hybrid search",
    "bm25",
    "rrf",
    "pgvector",
    "postgres",
    "kubernetes",
    "k8s",
    "production",
    "cost",
    "memory",
    "sync",
    "pipeline",
    "tutorial",
    "how to",
    "code",
    "python",
    "go",
    "sql",
    "failure",
    "tradeoff",
    "trade-off",
    "evaluation",
]

OFFICIAL_CONTEXT = [
    "release",
    "announcement",
    "community",
    "support",
    "policy",
]


def norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def count_matches(text, keywords):
    lowered = norm(text)
    return sum(1 for kw in keywords if kw.lower() in lowered)


def matching_terms(text, keywords):
    lowered = norm(text)
    return [kw for kw in keywords if kw.lower() in lowered]


def fetch_text(url):
    if not url:
        return ""
    py = VENV_PY if VENV_PY.exists() else Path(sys.executable)
    try:
        res = subprocess.run(
            [str(py), str(FETCH), url],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if res.returncode != 0:
            return ""
        return res.stdout
    except Exception:
        return ""


def topic_matches(text, topics):
    scored = []
    for topic in topics:
        topic_words = [
            word for word in re.split(r"[^a-zA-Z0-9]+", topic["topic"].lower())
            if len(word) > 3
        ]
        terms = [topic["topic"]] + topic.get("angles", []) + topic_words
        score = count_matches(text, terms)
        if score:
            scored.append({
                "topic": topic["topic"],
                "score": score,
                "subreddits": topic.get("good_subreddits", []),
            })
    scored.sort(key=lambda t: (-t["score"], t["topic"]))
    return scored


def suitability(text, has_full_body):
    lowered = norm(text)
    word_count = len(re.findall(r"\b\w+\b", lowered))
    positives = matching_terms(lowered, POSITIVE_SIGNALS)
    reject_hits = []
    for group, terms in REJECT_SIGNALS.items():
        hits = matching_terms(lowered, terms)
        reject_hits.extend([f"{group}:{hit}" for hit in hits])

    score = len(set(positives)) * 2 - len(reject_hits) * 3
    if has_full_body and word_count and word_count < 350:
        score -= 3
        reject_hits.append("thin_content:<350_words")

    if not has_full_body:
        status = "borderline" if score >= 0 else "unsuitable"
    elif score >= 8:
        status = "suitable"
    elif score >= 3:
        status = "borderline"
    else:
        status = "unsuitable"

    reasons = []
    if positives:
        reasons.append("technical signals: " + ", ".join(positives[:10]))
    if reject_hits:
        reasons.append("risk signals: " + ", ".join(reject_hits[:8]))
    if word_count:
        reasons.append(f"word_count={word_count}")
    else:
        reasons.append("word_count=unknown")
    if not has_full_body:
        reasons.append("full_body_not_fetched")

    return status, score, reasons


def assignment_scores(text, account_rules, topics):
    topic_hits = topic_matches(text, topics)
    topic_names = {t["topic"] for t in topic_hits[:4]}
    lowered = norm(text)

    rows = []
    for rule in account_rules:
        kw_score = count_matches(lowered, rule.get("keyword_signals", []))
        topic_score = sum(2 for t in rule.get("preferred_topics", []) if t in topic_names)
        score = kw_score + topic_score

        if rule.get("official_only"):
            official_hit = count_matches(lowered, OFFICIAL_CONTEXT)
            brand_hit = count_matches(lowered, ["milvus", "zilliz"])
            if not (official_hit and brand_hit):
                score -= 10

        rows.append({
            "account_code": rule["account_code"],
            "score": score,
            "keyword_hits": matching_terms(lowered, rule.get("keyword_signals", []))[:10],
            "preferred_subreddits": rule.get("preferred_subreddits", []),
            "preferred_topics": rule.get("preferred_topics", []),
            "rationale": rule.get("assignment_reason", ""),
        })

    rows.sort(key=lambda r: (-r["score"], r["account_code"]))
    return rows, topic_hits


def choose_subreddits(row, topic_hits):
    topic_subs = []
    for topic in topic_hits[:3]:
        topic_subs.extend(topic.get("subreddits", []))
    preferred = row.get("preferred_subreddits", [])
    ranked = []
    for sub in [s for s in preferred if s in topic_subs] + preferred:
        if sub not in ranked:
            ranked.append(sub)
    return ranked


def screen_row(row, account_rules, topics, top_n, no_fetch):
    title = row.get("title") or row.get("blog_title") or ""
    notes = row.get("notes", "")
    url = row.get("url") or row.get("blog_url") or ""
    fetched = "" if no_fetch else fetch_text(url)
    text = "\n".join([title, url, notes, fetched or ""]).strip()

    status, score, reasons = suitability(text, bool(fetched))
    scored_accounts, topic_hits = assignment_scores(text, account_rules, topics)

    assignments = []
    if status != "unsuitable":
        eligible = [r for r in scored_accounts if r["score"] >= 3]
        if not eligible:
            eligible = scored_accounts[:1]
        for acct in eligible[:top_n]:
            recommended_subreddits = choose_subreddits(acct, topic_hits)
            recommended_post_types = {
                subreddit: weekly_post_rules.recommend_post_type(subreddit, text)
                for subreddit in recommended_subreddits
            }
            assignments.append({
                "account_code": acct["account_code"],
                "score": acct["score"],
                "recommended_subreddits": recommended_subreddits,
                "recommended_post_types": recommended_post_types,
                "recommended_link_policies": {
                    subreddit: weekly_post_rules.recommend_link_policy(
                        acct["account_code"], subreddit, recommended_post_types[subreddit]
                    )
                    for subreddit in recommended_subreddits
                },
                "recommended_topics": [
                    t for t in acct.get("preferred_topics", [])
                    if t in {hit["topic"] for hit in topic_hits[:4]}
                ] or [hit["topic"] for hit in topic_hits[:2]],
                "rationale": acct["rationale"],
                "keyword_hits": acct["keyword_hits"],
            })

    return {
        "blog_id": row.get("blog_id", ""),
        "title": title,
        "url": url,
        "suitability": status,
        "suitability_score": score,
        "reasons": reasons,
        "topic_matches": topic_hits[:5],
        "assignments": assignments,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="screen one blog URL")
    ap.add_argument("--title", default="", help="title for --url")
    ap.add_argument("--top-n", type=int, default=2, help="assign at most the fitting R1/R2 accounts; default 2")
    ap.add_argument("--no-fetch", action="store_true", help="score only title/notes without fetching URL")
    args = ap.parse_args()

    top_n = max(1, min(args.top_n, 2))
    account_rules = json.loads(RULES.read_text())
    active_accounts = set(weekly_post_rules.load_rules().get("active_accounts", []))
    account_rules = [
        rule for rule in account_rules
        if rule.get("account_code") in active_accounts
    ]
    topics = json.loads(TOPICS.read_text())

    rows = [{
        "blog_id": "",
        "title": args.title,
        "url": args.url,
        "notes": "",
    }]

    results = [screen_row(r, account_rules, topics, top_n, args.no_fetch) for r in rows]
    payload = {"count": len(results), "results": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
