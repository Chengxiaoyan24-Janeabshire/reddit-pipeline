#!/usr/bin/env python3
"""List rows from the Feishu Reddit Blog Pool."""
import argparse
import json

import feishu_client
import weekly_post_rules


def as_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_list(value):
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("name") or item.get("value")
                if text:
                    out.append(text)
            elif item:
                out.append(str(item))
        return out
    text = feishu_client.extract_text(value)
    return [t.strip() for t in text.split(",") if t.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    ids = feishu_client.get_table_ids()
    app_token = ids["reddit_bitable_app_token"]
    pool_table = ids["reddit_blog_pool_table_id"]
    out = []
    for item in feishu_client.list_records(app_token, pool_table):
        fields = item.get("fields", {})
        row = {
            "record_id": item["record_id"],
            "blog_url": feishu_client.extract_url(fields.get("Blog URL")),
            "blog_title": feishu_client.extract_text(fields.get("Blog 标题")),
            "publish_date": fields.get("Publish Date"),
            "recent_priority": weekly_post_rules.is_recent_source(fields.get("Publish Date")),
            "url_status": feishu_client.extract_text(fields.get("URL 状态")),
            "screening_status": feishu_client.extract_text(fields.get("筛选状态")),
            "screening_score": fields.get("筛选分数", 0),
            "topic_tags": as_list(fields.get("匹配 Topic Tags")),
            "assigned_accounts": as_list(fields.get("推荐 Account Tags")),
            "recommended_subreddits": as_list(fields.get("推荐 Subreddit Tags")) or as_list(fields.get("推荐 Subreddits")),
            "matched_keywords": feishu_client.extract_text(fields.get("匹配关键词")),
            "assigned_accounts_json_legacy": feishu_client.extract_text(fields.get("Assigned Accounts JSON")),
            "topic_matches_json_legacy": feishu_client.extract_text(fields.get("Topic 匹配 JSON")),
            "generated_count": as_int(fields.get("已生成内容数")),
        }
        if not args.all:
            if row["url_status"] not in {"", "Active"}:
                continue
            if row["generated_count"] > 0:
                continue
        out.append(row)
    out.sort(key=lambda row: weekly_post_rules.source_priority_key(row["publish_date"]))
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
