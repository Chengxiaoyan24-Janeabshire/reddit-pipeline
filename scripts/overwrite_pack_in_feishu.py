#!/usr/bin/env python3
"""Overwrite existing Reddit review Docs without creating new rows."""
import argparse
import json
import re
import sys

import append_pack
import append_pack_to_feishu
import feishu_client
import feishu_docs


def doc_token(value):
    url = feishu_client.extract_url(value)
    match = re.search(r"/docx/([A-Za-z0-9]+)", url or "")
    return match.group(1) if match else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft-ids", nargs="+", required=True)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    specs = append_pack_to_feishu.normalize_payload(json.load(sys.stdin))
    errors = [] if args.partial else append_pack_to_feishu.validate_weekly_specs(specs)
    for index, spec in enumerate(specs, 1):
        item_errors, _ = append_pack.validate(spec)
        errors.extend(f"pack[{index}]: {error}" for error in item_errors)
    items = [(spec, item) for spec in specs for item in spec.get("items", [])]
    if len(items) != len(args.draft_ids):
        errors.append(
            f"draft-id count {len(args.draft_ids)} does not match item count {len(items)}"
        )
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        sys.exit(1)

    ids = feishu_client.get_table_ids()
    rows = feishu_client.list_records(
        ids["reddit_bitable_app_token"],
        ids["reddit_persona_pipeline_table_id"],
    )
    by_draft_id = {
        feishu_client.extract_text(row.get("fields", {}).get("Draft ID")): row
        for row in rows
    }
    bindings = []
    for draft_id, (spec, item) in zip(args.draft_ids, items):
        row = by_draft_id.get(draft_id)
        if not row:
            errors.append(f"missing target Draft ID {draft_id}")
            continue
        fields = row.get("fields", {})
        existing_account = feishu_client.extract_text(fields.get("Account Code"))
        existing_subreddit = fields.get("Subreddit") or []
        if existing_account != item.get("account_code"):
            errors.append(f"{draft_id}: account mismatch")
        if item.get("subreddit") not in existing_subreddit:
            errors.append(f"{draft_id}: subreddit mismatch")
        token = doc_token(fields.get("Content Doc"))
        if not token:
            errors.append(f"{draft_id}: missing Content Doc token")
        bindings.append({
            "draft_id": draft_id,
            "record_id": row.get("record_id"),
            "document_id": token,
            "account_code": item.get("account_code"),
            "subreddit": item.get("subreddit"),
            "markdown": append_pack_to_feishu.build_content_markdown(item),
        })
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        sys.exit(1)

    preview = [{k: value for k, value in binding.items() if k != "markdown"} | {
        "characters": len(binding["markdown"])
    } for binding in bindings]
    if not args.write:
        print(json.dumps({"ok": True, "dry_run": True, "would_overwrite": preview}, ensure_ascii=False, indent=2))
        return

    updated = []
    for binding in bindings:
        feishu_docs.replace_blocks(
            binding["document_id"],
            feishu_docs.markdown_to_blocks(binding["markdown"]),
        )
        updated.append(binding["draft_id"])
    print(json.dumps({"ok": True, "overwritten": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
