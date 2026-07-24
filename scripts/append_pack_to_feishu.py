#!/usr/bin/env python3
"""Validate Reddit draft packs, create Feishu Content Docs, and append rows."""
import argparse
import json
import re
import sys
from datetime import date

import append_pack
import feishu_client
import feishu_docs
import weekly_post_rules

DATE_ID_RE = re.compile(r"^RD-\d{4}-\d{2}-\d{2}-")
DEFAULT_PUBLISH_STATUS = "Pending"


def existing_count_today(app_token, table_id):
    today = date.today().isoformat()
    count = 0
    for item in feishu_client.list_records(app_token, table_id):
        draft_id = feishu_client.extract_text(item.get("fields", {}).get("Draft ID"))
        if draft_id.startswith(f"RD-{today}-"):
            count += 1
    return count


def bump_pool_count(app_token, pool_table, record_id, delta):
    if not record_id:
        return None
    records = feishu_client.list_records(app_token, pool_table)
    target = next((r for r in records if r["record_id"] == record_id), None)
    if not target:
        return None
    fields = target.get("fields", {})
    try:
        current = int(fields.get("已生成内容数") or 0)
    except (TypeError, ValueError):
        current = 0
    new_value = current + delta
    feishu_client.update_record(app_token, pool_table, record_id, {
        "已生成内容数": new_value,
        "URL 状态": "In Use",
    })
    return new_value


def load_pool_publish_dates(app_token, pool_table, record_ids):
    wanted = {record_id for record_id in record_ids if record_id}
    if not wanted:
        return {}
    return {
        record["record_id"]: record.get("fields", {}).get("Publish Date")
        for record in feishu_client.list_records(app_token, pool_table)
        if record.get("record_id") in wanted
    }


def uniq(values):
    out = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def normalize_screening_status(value):
    mapping = {
        "suitable": "Suitable",
        "borderline": "Borderline",
        "unsuitable": "Unsuitable",
        "needs review": "Needs Review",
        "needs_review": "Needs Review",
        "pending": "Pending",
    }
    text = str(value or "").strip()
    return mapping.get(text.lower(), text if text else "Pending")


def load_topic_names():
    topics_path = append_pack.ROOT / "data" / "topic_bank.json"
    if not topics_path.exists():
        return []
    return [t.get("topic", "") for t in json.loads(topics_path.read_text()) if t.get("topic")]


def match_topic_tags(text, topic_names):
    lowered = (text or "").lower()
    matches = []
    for topic in topic_names:
        topic_words = [
            word for word in re.split(r"[^a-zA-Z0-9]+", topic.lower())
            if len(word) > 3
        ]
        if topic.lower() in lowered or any(word in lowered for word in topic_words):
            matches.append(topic)
    return matches[:3]


def screening_topic_tags(screening, items, topic_names):
    values = []
    for key in ("topic_tags", "topics", "source_topic_tags"):
        raw = screening.get(key)
        if isinstance(raw, list):
            values.extend(raw)
        elif raw:
            values.append(raw)
    for raw in screening.get("topic_matches", []) or []:
        if isinstance(raw, dict):
            values.append(raw.get("topic"))
        else:
            values.append(raw)
    if not values:
        values.extend(
            tag
            for item in items
            for tag in match_topic_tags(
                "\n".join([item.get("title", ""), item.get("angle", ""), item.get("body", "")]),
                topic_names,
            )
        )
    return uniq(values)


def screening_account_tags(screening, items):
    raw = screening.get("assigned_accounts") or screening.get("account_tags") or []
    values = raw if isinstance(raw, list) else [raw]
    values.extend(item.get("account_code") for item in items)
    return uniq(values)


def build_drafts(spec, start_seq, topic_names):
    accounts = append_pack.load_accounts()
    today = date.today().isoformat()
    drafts = []
    for offset, item in enumerate(spec["items"]):
        code = item["account_code"]
        account = accounts.get(code, {})
        content_type = item.get("content_type", "technical_post")
        body = item.get("body", "") or item.get("post", "") or ""
        title = item.get("title", "") or ""
        length_tier = append_pack.infer_length_tier(item)
        code_language = append_pack.infer_code_language(item)
        subreddit = item.get("subreddit", "")
        default_voice = account.get("voice_fingerprint_id", "")
        topic_tags = item.get("topic_tags") or item.get("topics") or match_topic_tags(
            "\n".join([title, item.get("angle", ""), body]),
            topic_names,
        )
        drafts.append({
            "draft_id": f"RD-{today}-{start_seq + offset:03d}",
            "account_code": code,
            "account_role": account.get("role", ""),
            "content_type": content_type,
            "subreddit": subreddit,
            "post_type": item.get("post_type", ""),
            "suggested_day": item.get("suggested_day", ""),
            "title": title,
            "body": body,
            "milvus_mention_basis": item.get("milvus_mention_basis", ""),
            "disclosure": item.get("disclosure", ""),
            "link_policy": item.get("link_policy", "no_link"),
            "angle": item.get("angle", ""),
            "voice_fingerprint": item.get("voice_fingerprint", "") or default_voice,
            "length_tier": length_tier,
            "code_language": code_language,
            "code_allowed": length_tier == "code_long_post",
            "topic_tags": uniq(topic_tags),
            "char_count": len(body),
        })
    return drafts


def build_content_markdown(draft):
    return draft["body"].strip() + "\n"


def as_url_field(url):
    return {"link": url, "text": url}


def subreddit_value(draft, existing_field_names):
    value = draft["subreddit"]
    if not value:
        return []
    if "Draft Subreddit Tags" in existing_field_names:
        return value
    return [value]


def filter_existing_fields(record, existing_field_names):
    return {k: v for k, v in record.items() if k in existing_field_names and v not in (None, [], "")}


def build_records(spec, drafts, doc_url, existing_field_names, inline_content=False):
    source_url = spec.get("source_url", "")
    screening = spec.get("screening", {}) or {}
    topic_names = load_topic_names()
    source_topics = screening_topic_tags(screening, spec["items"], topic_names)
    assigned_accounts = screening_account_tags(screening, spec["items"])
    screening_status = normalize_screening_status(screening.get("status") or screening.get("suitability"))
    try:
        screening_score = int(screening.get("score") or screening.get("suitability_score") or 0)
    except (TypeError, ValueError):
        screening_score = 0

    records = []
    for draft in drafts:
        record = {
            "Draft ID": draft["draft_id"],
            "Source Blog 标题": spec.get("source_title", ""),
            "Blog Pool Record ID": spec.get("pool_record_id", "") or spec.get("pool_blog_id", ""),
            "Source Blog Publish Date": spec.get("source_publish_date", ""),
            "Account Code": draft["account_code"],
            "Account Role": draft["account_role"],
            "Subreddit": subreddit_value(draft, existing_field_names),
            "Post Type": draft["post_type"],
            "Draft Subreddit Tags": [draft["subreddit"]] if draft["subreddit"] else [],
            "Suggested Day": draft["suggested_day"],
            "Title": draft["title"],
            "Body": build_content_markdown(draft).rstrip() if inline_content or not doc_url else "",
            "Link Policy": draft["link_policy"],
            "Milvus Mention Basis": draft["milvus_mention_basis"],
            "Angle": draft["angle"],
            "Voice Fingerprint": draft["voice_fingerprint"],
            "Source Screening Status": screening_status,
            "Source Screening Score": screening_score,
            "Source Topic Tags": source_topics,
            "Assigned Account Tags": assigned_accounts,
            "Draft Topic Tags": draft["topic_tags"],
            "Length Tier": draft["length_tier"],
            "Code Allowed": draft["code_allowed"],
            "字符数": draft["char_count"],
            "Status": DEFAULT_PUBLISH_STATUS,
            "Publish URL": "",
            "Publish Date": "",
            "Publisher": "",
            "Reviewer Notes": "",
        }
        if draft["code_language"]:
            record["Code Language"] = draft["code_language"]
        if source_url:
            record["Source Blog URL"] = as_url_field(source_url)
        if doc_url:
            record["Content Doc"] = as_url_field(doc_url)
        records.append(filter_existing_fields(record, existing_field_names))
    return records


def normalize_payload(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise ValueError("Input must be a pack object or a list of pack objects.")


def validate_weekly_specs(specs):
    expected = {
        (slot["account_code"], slot["subreddit"])
        for slot in weekly_post_rules.load_rules().get("weekly_slots", [])
    }
    actual = [
        (item.get("account_code", ""), item.get("subreddit", ""))
        for spec in specs
        for item in spec.get("items", [])
    ]
    errors = []
    if len(actual) != len(expected):
        errors.append(f"weekly run must contain exactly {len(expected)} drafts; got {len(actual)}")
    duplicates = sorted({slot for slot in actual if actual.count(slot) > 1})
    if duplicates:
        errors.append(f"weekly run has duplicate account/subreddit slots: {duplicates}")
    missing = sorted(expected - set(actual))
    unexpected = sorted(set(actual) - expected)
    if missing:
        errors.append(f"weekly run is missing slots: {missing}")
    if unexpected:
        errors.append(f"weekly run has unexpected slots: {unexpected}")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--weekly", action="store_true", help="require exactly the four configured R1/R2 weekly slots")
    ap.add_argument("--dry-run", action="store_true", help="preview records without creating docs or writing Feishu rows")
    ap.add_argument("--no-doc", action="store_true", help="skip Feishu Doc creation and write body inline")
    ap.add_argument("--inline-content", action="store_true", help="also write Body into the table")
    args = ap.parse_args()

    try:
        payload = json.load(sys.stdin)
        specs = normalize_payload(payload)
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        sys.exit(1)

    all_errors = []
    all_warnings = []
    if args.weekly:
        all_errors.extend(validate_weekly_specs(specs))
    for spec_index, spec in enumerate(specs, 1):
        errors, warnings = append_pack.validate(spec)
        all_errors.extend([f"pack[{spec_index}]: {e}" for e in errors])
        all_warnings.extend([f"pack[{spec_index}]: {w}" for w in warnings])

    if all_errors:
        print(json.dumps({"ok": False, "errors": all_errors, "warnings": all_warnings}, ensure_ascii=False, indent=2))
        sys.exit(1)
    if args.validate_only:
        print(json.dumps({
            "ok": True,
            "packs": len(specs),
            "validated": sum(len(spec.get("items", [])) for spec in specs),
            "warnings": all_warnings,
        }, ensure_ascii=False, indent=2))
        return

    ids = feishu_client.get_table_ids()
    app_token = ids["reddit_bitable_app_token"]
    pipeline_table = ids["reddit_persona_pipeline_table_id"]
    pool_table = ids["reddit_blog_pool_table_id"]
    folder_token = ids.get("reddit_doc_folder_token") or ids.get("output_folder_token")
    base_url = ids.get("base_url", "https://zilliverse.feishu.cn")
    existing_field_names = {
        field.get("field_name")
        for field in feishu_client.list_fields(app_token, pipeline_table)
    }
    topic_names = load_topic_names()

    if not args.no_doc and not args.dry_run and not folder_token:
        print(json.dumps({
            "ok": False,
            "errors": ["Missing reddit_doc_folder_token/output_folder_token in Feishu config."],
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    start_seq = existing_count_today(app_token, pipeline_table) + 1
    pool_publish_dates = load_pool_publish_dates(
        app_token,
        pool_table,
        [spec.get("pool_record_id") or spec.get("pool_blog_id") for spec in specs],
    )
    all_records = []
    doc_urls = []
    pool_deltas = []
    doc_warnings = []

    for spec in specs:
        pool_record_id = spec.get("pool_record_id") or spec.get("pool_blog_id")
        if pool_record_id and not spec.get("source_publish_date"):
            spec = dict(spec)
            spec["source_publish_date"] = pool_publish_dates.get(pool_record_id, "")
        drafts = build_drafts(spec, start_seq, topic_names)
        start_seq += len(drafts)
        spec_record_count = 0
        for draft in drafts:
            doc_url = ""
            if not args.no_doc and not args.dry_run:
                doc_title = draft["title"] or draft["draft_id"]
                markdown = build_content_markdown(draft)
                doc_url, warnings = feishu_docs.create_doc_from_markdown(doc_title, markdown, folder_token, base_url)
                doc_urls.append(doc_url)
                doc_warnings.extend(warnings)
            elif args.dry_run and not args.no_doc:
                doc_url = f"{base_url.rstrip('/')}/docx/dry-run-{draft['draft_id']}"
                doc_urls.append(f"(dry-run: would create Feishu Doc for {draft['draft_id']})")
            records = build_records(
                spec,
                [draft],
                doc_url,
                existing_field_names,
                inline_content=args.inline_content or args.no_doc,
            )
            all_records.extend(records)
            spec_record_count += len(records)
        pool_deltas.append((spec.get("pool_record_id") or spec.get("pool_blog_id"), spec_record_count))

    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "dry_run": True,
            "would_write": len(all_records),
            "doc_urls": doc_urls,
            "first_record": all_records[0] if all_records else None,
            "warnings": all_warnings,
        }, ensure_ascii=False, indent=2))
        return

    feishu_client.batch_create_records(app_token, pipeline_table, all_records)
    pool_counts = []
    for record_id, delta in pool_deltas:
        pool_counts.append({
            "pool_record_id": record_id,
            "pool_count_now": bump_pool_count(app_token, pool_table, record_id, delta),
        })

    print(json.dumps({
        "ok": True,
        "written": len(all_records),
        "doc_urls": doc_urls,
        "pool_counts": pool_counts,
        "warnings": all_warnings + doc_warnings,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
