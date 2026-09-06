#!/usr/bin/env python3
"""Sync rows that satisfy the configured Reddit source contract."""
import argparse
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import feishu_client
import official_blog_catalog
import resource_paths
import weekly_post_rules

SOURCE_RULES = json.loads(resource_paths.SOURCE_SYNC_RULES.read_text())
DEFAULT_SINCE = SOURCE_RULES["minimum_publish_date"]
DEFAULT_SOURCE_APP = SOURCE_RULES["source_app_token"]
DEFAULT_SOURCE_TABLE = SOURCE_RULES["source_table_id"]
DEFAULT_SOURCE_VIEW = SOURCE_RULES["source_view_id"]
REQUIRED_CATEGORY = SOURCE_RULES["category"]
REQUIRED_STATUS = SOURCE_RULES["status"]
OFFICIAL_HOSTS = set(SOURCE_RULES["official_hosts"])
REQUIRED_PATH_PREFIX = SOURCE_RULES["required_path_prefix"]
AUTHOR_SYNC_POLICY = SOURCE_RULES.get("author_sync_policy", {})
AUTHOR_FIELD_CANDIDATES = AUTHOR_SYNC_POLICY.get("source_field_candidates", ["Author"])
ALWAYS_SYNC_AUTHORS = {
    str(author).strip().casefold()
    for author in AUTHOR_SYNC_POLICY.get("always_sync_authors", [])
    if str(author).strip()
}


def require_all_content_source(app_token, table_id, view_id):
    configured = (app_token, table_id, view_id)
    required = (DEFAULT_SOURCE_APP, DEFAULT_SOURCE_TABLE, DEFAULT_SOURCE_VIEW)
    if configured != required:
        raise RuntimeError(
            f"Reddit pool sync must read {SOURCE_RULES['source_name']} "
            f"{required}; configured source is {configured}. Excluded sources: "
            f"{', '.join(SOURCE_RULES.get('excluded_sources', []))}."
        )


def parse_since(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("--since-date must use YYYY-MM-DD") from exc


def norm_url(url):
    return official_blog_catalog.canonical_url(url)


def source_publish_date(value):
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    return official_blog_catalog.parse_date(feishu_client.extract_text(value))


def clean_title(value):
    title = feishu_client.extract_text(value)
    for prefix in ("Blog Post:", "Blog post:", "Blog:", "blog:", "Blog：", "blog："):
        if title.startswith(prefix):
            return title[len(prefix):].strip()
    return title


def source_author(fields, metadata=None):
    author = (metadata or {}).get("author")
    if author:
        return feishu_client.extract_text(author).strip()
    for field_name in AUTHOR_FIELD_CANDIDATES:
        author = feishu_client.extract_text(fields.get(field_name)).strip()
        if author:
            return author
    return ""


def is_always_sync_author(author):
    return str(author or "").strip().casefold() in ALWAYS_SYNC_AUTHORS


def is_official_blog_url(url):
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    return (
        parsed.netloc.lower() in OFFICIAL_HOSTS
        and bool(path_parts)
        and path_parts[0] == REQUIRED_PATH_PREFIX
    )


def filter_existing_fields(fields, existing_field_names):
    return {
        key: value
        for key, value in fields.items()
        if key in existing_field_names and value not in (None, [], "")
    }


def source_candidates(app_token, table_id, view_id, catalog, since):
    deduped = {}
    skipped_unknown_date = []
    skipped_before_since = 0
    skipped_non_blog = 0
    skipped_missing_url = 0
    skipped_not_published = 0
    for item in feishu_client.list_records(app_token, table_id, view_id=view_id):
        fields = item.get("fields", {})
        if feishu_client.extract_text(fields.get("Category")) != REQUIRED_CATEGORY:
            continue
        if (
            feishu_client.extract_text(fields.get("Status")).strip().lower()
            != REQUIRED_STATUS.lower()
        ):
            skipped_not_published += 1
            continue
        url = feishu_client.extract_url(fields.get("Publish URL"))
        if not url:
            skipped_missing_url += 1
            continue
        if not is_official_blog_url(url):
            skipped_non_blog += 1
            continue
        metadata = official_blog_catalog.lookup(catalog, url)
        published_at = source_publish_date(fields.get("Publish Date"))
        if not metadata and not published_at:
            try:
                metadata = official_blog_catalog.fetch_article_metadata(url)
            except Exception:
                metadata = None
        published_at = (metadata or {}).get("published_at") or published_at
        if not published_at:
            skipped_unknown_date.append({"record_id": item["record_id"], "url": url})
            continue
        author = source_author(fields, metadata)
        if (
            published_at < since
            and not (
                AUTHOR_SYNC_POLICY.get("bypass_minimum_publish_date")
                and is_always_sync_author(author)
            )
        ):
            skipped_before_since += 1
            continue
        canonical = norm_url((metadata or {}).get("url") or url)
        deduped.setdefault(canonical, {
            "record_id": item["record_id"],
            "url": (metadata or {}).get("url") or url,
            "title": (metadata or {}).get("title") or clean_title(fields.get("Title & Topic")),
            "source_author": author,
            "always_sync_author": is_always_sync_author(author),
            "publish_date": int(published_at.timestamp() * 1000),
        })
    candidates = sorted(
        deduped.values(),
        key=lambda row: weekly_post_rules.source_priority_key(row["publish_date"]),
    )
    return (
        candidates,
        skipped_unknown_date,
        skipped_before_since,
        skipped_non_blog,
        skipped_missing_url,
        skipped_not_published,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since-date", default=DEFAULT_SINCE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ids = feishu_client.get_table_ids()
    target_app = ids["reddit_bitable_app_token"]
    target_table = ids["reddit_blog_pool_table_id"]
    source_app = ids.get("source_content_app_token", DEFAULT_SOURCE_APP)
    source_table = ids.get("source_content_table_id", DEFAULT_SOURCE_TABLE)
    source_view = ids.get("source_content_view_id", DEFAULT_SOURCE_VIEW)
    require_all_content_source(source_app, source_table, source_view)
    since = parse_since(args.since_date)

    catalog = official_blog_catalog.build_catalog()
    candidates, unknown_date, before_since, non_blog, missing_url, not_published = source_candidates(
        source_app, source_table, source_view, catalog, since
    )
    existing_fields = {
        field.get("field_name")
        for field in feishu_client.list_fields(target_app, target_table)
    }
    existing_urls = {
        norm_url(feishu_client.extract_url(item.get("fields", {}).get("Blog URL")))
        for item in feishu_client.list_records(target_app, target_table)
        if feishu_client.extract_url(item.get("fields", {}).get("Blog URL"))
    }
    new_items = [row for row in candidates if norm_url(row["url"]) not in existing_urls]
    recency_rules = weekly_post_rules.load_rules()
    priority_days = weekly_post_rules.priority_window_days(recency_rules)
    cutoff = weekly_post_rules.recent_cutoff(rules=recency_rules)
    for row in candidates:
        row["recent_priority"] = weekly_post_rules.is_recent_source(
            row["publish_date"], rules=recency_rules
        )
    records = [
        filter_existing_fields({
            "Blog URL": {"link": row["url"], "text": row["url"]},
            "Blog 标题": row["title"],
            "Source Type": SOURCE_RULES["source_type_label"],
            "Source Record ID": row["record_id"],
            "Source Author": row["source_author"],
            "Publish Date": row["publish_date"],
            "URL 状态": "Active",
            "筛选状态": "Pending",
            "已生成内容数": 0,
        }, existing_fields)
        for row in new_items
    ]
    if records and not args.dry_run:
        feishu_client.batch_create_records(target_app, target_table, records)

    print(json.dumps({
        "source": (
            f"{SOURCE_RULES['source_name']} / Category={REQUIRED_CATEGORY} / "
            f"Status={REQUIRED_STATUS}"
        ),
        "source_app_token": source_app,
        "source_table_id": source_table,
        "source_view_id": source_view,
        "since_date": args.since_date,
        "priority_window_days": priority_days,
        "recent_cutoff": cutoff.date().isoformat(),
        "recent_eligible": sum(1 for row in candidates if row["recent_priority"]),
        "recent_new": sum(1 for row in new_items if row["recent_priority"]),
        "eligible_unique": len(candidates),
        "already_in_pool": len(candidates) - len(new_items),
        "new": len(new_items),
        "always_sync_author_eligible": sum(
            1 for row in candidates if row["always_sync_author"]
        ),
        "always_sync_author_new": sum(
            1 for row in new_items if row["always_sync_author"]
        ),
        "written": 0 if args.dry_run else len(records),
        "skipped_before_since": before_since,
        "skipped_non_blog": non_blog,
        "skipped_missing_url": missing_url,
        "skipped_not_published": not_published,
        "skipped_unknown_date": unknown_date,
        "dry_run": args.dry_run,
        "items": new_items,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
