#!/usr/bin/env python3
"""Create Reddit-specific Feishu Bitable tables in the configured base.

The script creates these tables if they do not already exist:
  - Reddit Blog Pool
  - Reddit Persona Pipeline

It writes public table ids to config/feishu-tables.json. Credentials are read by
feishu_client.py and are not copied into that public table config.
"""
import json

import feishu_client
import reddit_browser_monitor
import resource_paths
import weekly_post_rules

ROOT = resource_paths.ROOT
TABLE_CONFIG = ROOT / "config" / "feishu-tables.json"
DEFAULT_APP_TOKEN = "MGwdb5fDga283QsoQb0cwWGFnYe"
ACCOUNTS = resource_paths.ACCOUNTS
SUBREDDITS = resource_paths.SUBREDDITS
TOPICS = resource_paths.TOPIC_BANK
LENGTH_RULES = resource_paths.CONTENT_LENGTH_RULES
USER_FINGERPRINTS = resource_paths.USER_FINGERPRINTS
SOURCE_SYNC_RULES = json.loads(resource_paths.SOURCE_SYNC_RULES.read_text())


def single_select(options):
    return {
        "options": [
            {"name": name, "color": i % 14}
            for i, name in enumerate(options)
        ]
    }


def multi_select(options):
    return single_select(options)


def number(fmt="0"):
    return {"formatter": fmt}


def date_prop():
    return {"date_formatter": "yyyy/MM/dd"}


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def api_field(field):
    return {k: v for k, v in field.items() if not k.startswith("_")}


def option_values():
    weekly_rules = weekly_post_rules.load_rules()
    accounts = [a["account_code"] for a in load_json(ACCOUNTS, [])]
    subreddits = [s["name"] for s in load_json(SUBREDDITS, [])]
    subreddits = list(dict.fromkeys(subreddits))
    topics = [t["topic"] for t in load_json(TOPICS, [])]
    length_rows = load_json(LENGTH_RULES, [])
    length_tiers = [r["tier"] for r in length_rows]
    voice_fingerprints = [
        f["fingerprint_id"]
        for f in load_json(USER_FINGERPRINTS, [])
        if f.get("fingerprint_id")
    ]
    code_languages = list(dict.fromkeys(
        language
        for row in length_rows
        for language in row.get("preferred_code_languages", [])
    ))
    post_types = list(dict.fromkeys(
        post_type
        for slot in weekly_rules.get("weekly_slots", [])
        for post_type in slot.get("post_types", [])
    ))
    link_policies = list(weekly_rules.get("link_policy_modes", {}))
    return {
        "accounts": accounts or weekly_rules.get("active_accounts", []),
        "subreddits": subreddits,
        "topics": topics,
        "length_tiers": length_tiers,
        "voice_fingerprints": voice_fingerprints,
        "code_languages": code_languages,
        "post_types": post_types,
        "link_policies": link_policies,
    }


def build_schemas():
    opts = option_values()
    return {
        "Reddit Blog Pool": [
        {"field_name": "Blog URL", "type": 15},
        {"field_name": "Blog 标题", "type": 1},
        {"field_name": "Source Type", "type": 3, "property": single_select([SOURCE_SYNC_RULES["source_type_label"], "Manual"])},
        {"field_name": "Source Record ID", "type": 1},
        {"field_name": "Publish Date", "type": 5, "property": date_prop()},
        {"field_name": "上次筛选日期", "type": 5, "property": date_prop()},
        {"field_name": "URL 状态", "type": 3, "property": single_select(["Active", "In Use", "Archived", "Rejected"])},
        {"field_name": "筛选状态", "type": 3, "property": single_select(["Pending", "Suitable", "Borderline", "Unsuitable", "Needs Review"])},
        {"field_name": "筛选分数", "type": 2, "property": number("0")},
        {"field_name": "筛选原因", "type": 1},
        {"field_name": "已生成内容数", "type": 2, "property": number("0")},
        {"field_name": "主推荐 Topic", "type": 3, "property": single_select(opts["topics"])},
        {"field_name": "匹配 Topic Tags", "type": 4, "property": multi_select(opts["topics"])},
        {"field_name": "推荐 Account Tags", "type": 4, "property": multi_select(opts["accounts"]), "_replace_options": True},
        {"field_name": "推荐 Subreddit Tags", "type": 4, "property": multi_select(opts["subreddits"])},
        {"field_name": "推荐 Post Type Tags", "type": 4, "property": multi_select(opts["post_types"])},
        {"field_name": "推荐 Link Policy Tags", "type": 4, "property": multi_select(opts["link_policies"]), "_replace_options": True},
        {"field_name": "匹配关键词", "type": 1},
        {"field_name": "备注", "type": 1},
    ],
    "Reddit Persona Pipeline": [
        {"field_name": "Draft ID", "type": 1},
        {"field_name": "Source Blog 标题", "type": 1},
        {"field_name": "Source Blog URL", "type": 15},
        {"field_name": "Blog Pool Record ID", "type": 1},
        {"field_name": "Source Blog Publish Date", "type": 5, "property": date_prop()},
        {"field_name": "Subreddit", "type": 4, "property": multi_select(opts["subreddits"])},
        {"field_name": "Account Code", "type": 3, "property": single_select(opts["accounts"]), "_replace_options": True},
        {"field_name": "Account Role", "type": 1},
        {"field_name": "Content Doc", "type": 15},
        {"field_name": "Post Type", "type": 3, "property": single_select(opts["post_types"])},
        {"field_name": "Link Policy", "type": 3, "property": single_select(opts["link_policies"]), "_replace_options": True},
        {"field_name": "Milvus Mention Basis", "type": 1},
        {"field_name": "Draft Topic Tags", "type": 4, "property": multi_select(opts["topics"])},
        {"field_name": "Angle", "type": 1},
        {"field_name": "Voice Fingerprint", "type": 3, "property": single_select(opts["voice_fingerprints"])},
        {"field_name": "Length Tier", "type": 3, "property": single_select(opts["length_tiers"])},
        {"field_name": "字符数", "type": 2, "property": number("0")},
        {"field_name": "Status", "type": 3, "property": single_select(["Pending", "Published", "Cancel"]), "_replace_options": True},
        {"field_name": "Publish URL", "type": 15},
        {"field_name": "Publish Date", "type": 5, "property": date_prop()},
        {"field_name": "Publisher", "type": 3, "property": single_select(["Jenny", "Lumina"])},
        {"field_name": "Reviewer Notes", "type": 1},
    ] + reddit_browser_monitor.monitor_field_defs(),
    }

CONFIG_KEYS = {
    "Reddit Blog Pool": "reddit_blog_pool_table_id",
    "Reddit Persona Pipeline": "reddit_persona_pipeline_table_id",
}


def option_names(field):
    return {
        option.get("name")
        for option in (field.get("property") or {}).get("options", [])
        if option.get("name")
    }


def missing_select_options(existing_field, desired_field):
    if desired_field.get("type") not in {3, 4}:
        return []
    desired = option_names(desired_field)
    existing = option_names(existing_field)
    return [name for name in desired if name not in existing]


def merge_select_options(existing_field, desired_field):
    options = list((existing_field.get("property") or {}).get("options", []))
    existing_names = {option.get("name") for option in options}
    for option in (desired_field.get("property") or {}).get("options", []):
        if option.get("name") in existing_names:
            continue
        options.append({"name": option["name"], "color": option.get("color", len(options) % 14)})
    merged = dict(desired_field)
    merged["property"] = {"options": options}
    return merged


def replace_select_options(desired_field):
    options = []
    for option in (desired_field.get("property") or {}).get("options", []):
        options.append({"name": option["name"], "color": option.get("color", len(options) % 14)})
    merged = api_field(desired_field)
    merged["property"] = {"options": options}
    return merged


def ensure_fields(app_token, table_id, fields):
    existing = {f.get("field_name"): f for f in feishu_client.list_fields(app_token, table_id)}
    created = []
    updated = []
    for field in fields:
        current = existing.get(field["field_name"])
        if not current:
            feishu_client.create_field(app_token, table_id, api_field(field))
            created.append(field["field_name"])
            continue
        if field.get("_replace_options") and current.get("type") in {3, 4}:
            desired_names = [
                option.get("name")
                for option in (field.get("property") or {}).get("options", [])
                if option.get("name")
            ]
            current_names = [
                option.get("name")
                for option in (current.get("property") or {}).get("options", [])
                if option.get("name")
            ]
            if current_names != desired_names:
                feishu_client.update_field(
                    app_token,
                    table_id,
                    current["field_id"],
                    replace_select_options(field),
                )
                updated.append({"field": field["field_name"], "options_replaced": desired_names})
            continue
        missing_options = missing_select_options(current, field)
        if missing_options:
            feishu_client.update_field(
                app_token,
                table_id,
                current["field_id"],
                api_field(merge_select_options(current, field)),
            )
            updated.append({"field": field["field_name"], "options_added": missing_options})
    return created, updated


def main():
    table_ids = feishu_client.get_table_ids()
    app_token = table_ids.get("reddit_bitable_app_token") or table_ids.get("bitable_app_token") or DEFAULT_APP_TOKEN
    schemas = build_schemas()

    existing = {t["name"]: t for t in feishu_client.list_tables(app_token)}
    out = {
        "reddit_bitable_app_token": app_token,
        "source_content_app_token": table_ids.get(
            "source_content_app_token", SOURCE_SYNC_RULES["source_app_token"]
        ),
        "source_content_table_id": table_ids.get(
            "source_content_table_id", SOURCE_SYNC_RULES["source_table_id"]
        ),
        "source_content_view_id": table_ids.get(
            "source_content_view_id", SOURCE_SYNC_RULES["source_view_id"]
        ),
    }
    created = []
    reused = []
    fields_added = []
    fields_updated = []

    for name, fields in schemas.items():
        if name in existing:
            table = existing[name]
            reused.append({"name": name, "table_id": table["table_id"]})
            added, updated = ensure_fields(app_token, table["table_id"], fields)
            if added:
                fields_added.append({"name": name, "table_id": table["table_id"], "fields": added})
            if updated:
                fields_updated.append({"name": name, "table_id": table["table_id"], "fields": updated})
        else:
            table = feishu_client.create_table(app_token, name, [api_field(f) for f in fields], default_view_name="Grid")
            created.append({"name": name, "table_id": table["table_id"]})
        out[CONFIG_KEYS[name]] = table["table_id"]

    TABLE_CONFIG.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    print(json.dumps({
        "ok": True,
        "app_token": app_token,
        "created": created,
        "reused": reused,
        "fields_added": fields_added,
        "fields_updated": fields_updated,
        "config_written": str(TABLE_CONFIG),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
