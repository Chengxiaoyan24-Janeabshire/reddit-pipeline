#!/usr/bin/env python3
"""Run Reddit screening/assignment on Feishu Reddit Blog Pool rows and write JSON back."""
import argparse
import json
from datetime import datetime, timezone

import feishu_client
import screen_and_assign


def ms_now():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def as_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def uniq(values):
    out = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def filter_existing_fields(fields, existing_field_names):
    return {k: v for k, v in fields.items() if k in existing_field_names}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record-id")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ids = feishu_client.get_table_ids()
    app_token = ids["reddit_bitable_app_token"]
    pool_table = ids["reddit_blog_pool_table_id"]
    account_rules = json.loads(screen_and_assign.RULES.read_text())
    active_accounts = set(screen_and_assign.weekly_post_rules.load_rules().get("active_accounts", []))
    account_rules = [
        rule for rule in account_rules
        if rule.get("account_code") in active_accounts
    ]
    topics = json.loads(screen_and_assign.TOPICS.read_text())
    existing_field_names = {
        field.get("field_name")
        for field in feishu_client.list_fields(app_token, pool_table)
    }

    records = feishu_client.list_records(app_token, pool_table)
    records.sort(
        key=lambda item: screen_and_assign.weekly_post_rules.source_priority_key(
            item.get("fields", {}).get("Publish Date")
        )
    )
    results = []
    for item in records:
        if args.record_id and item["record_id"] != args.record_id:
            continue
        fields = item.get("fields", {})
        url_status = feishu_client.extract_text(fields.get("URL 状态"))
        if not args.record_id and url_status not in {"", "Active"}:
            continue
        if not args.record_id and as_int(fields.get("已生成内容数")) > 0:
            continue
        row = {
            "blog_id": item["record_id"],
            "title": feishu_client.extract_text(fields.get("Blog 标题")),
            "url": feishu_client.extract_url(fields.get("Blog URL")),
            "notes": feishu_client.extract_text(fields.get("备注")),
            "publish_date": fields.get("Publish Date"),
        }
        screened = screen_and_assign.screen_row(row, account_rules, topics, top_n=2, no_fetch=args.no_fetch)
        status_map = {
            "suitable": "Suitable",
            "borderline": "Borderline",
            "unsuitable": "Unsuitable",
        }
        subreddits = []
        post_types = []
        link_policies = []
        for assignment in screened.get("assignments", []):
            for sub in assignment.get("recommended_subreddits", []):
                if sub not in subreddits:
                    subreddits.append(sub)
            for post_type in assignment.get("recommended_post_types", {}).values():
                if post_type and post_type not in post_types:
                    post_types.append(post_type)
            for link_policy in assignment.get("recommended_link_policies", {}).values():
                if link_policy and link_policy not in link_policies:
                    link_policies.append(link_policy)
        topic_tags = uniq(t.get("topic") for t in screened.get("topic_matches", []))
        account_tags = uniq(a.get("account_code") for a in screened.get("assignments", []))
        keyword_hits = uniq(
            kw
            for assignment in screened.get("assignments", [])
            for kw in assignment.get("keyword_hits", [])
        )
        update = {
            "筛选状态": status_map.get(screened["suitability"], "Needs Review"),
            "筛选分数": screened["suitability_score"],
            "筛选原因": "\n".join(screened.get("reasons", [])),
            "主推荐 Topic": topic_tags[0] if topic_tags else "",
            "匹配 Topic Tags": topic_tags,
            "推荐 Account Tags": account_tags,
            "推荐 Subreddit Tags": subreddits,
            "推荐 Post Type Tags": post_types,
            "推荐 Link Policy Tags": link_policies,
            "匹配关键词": ", ".join(keyword_hits),
            "推荐 Subreddits": ", ".join(subreddits),
            "上次筛选日期": ms_now(),
            "Topic 匹配 JSON": "",
            "Assigned Accounts JSON": "",
        }
        if screened["suitability"] == "unsuitable":
            update["URL 状态"] = "Rejected"
        elif not url_status:
            update["URL 状态"] = "Active"

        update = filter_existing_fields(update, existing_field_names)
        if not args.dry_run:
            feishu_client.update_record(app_token, pool_table, item["record_id"], update)
        results.append({
            "record_id": item["record_id"],
            "title": row["title"],
            "url": row["url"],
            "publish_date": row["publish_date"],
            "recent_priority": screen_and_assign.weekly_post_rules.is_recent_source(
                row["publish_date"]
            ),
            "update": update,
            "assignments": screened.get("assignments", []),
        })
        if args.limit and len(results) >= args.limit:
            break

    print(json.dumps({
        "dry_run": args.dry_run,
        "updated": 0 if args.dry_run else len(results),
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
