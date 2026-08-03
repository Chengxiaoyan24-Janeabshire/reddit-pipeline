#!/usr/bin/env python3
"""Preview or write published Reddit metrics and comment signals to Feishu."""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import feishu_client
import reddit_post_monitor


ROOT = Path(__file__).resolve().parents[1]
FIELD_MAP_PATH = ROOT / "config" / "feishu-fields.json"
DEFAULT_USER_AGENT = "reddit-pipeline-monitor/1.0 (public JSON review workflow)"
SNAPSHOT_VERSION = 1


def load_field_map():
    if not FIELD_MAP_PATH.exists():
        return {}
    return json.loads(FIELD_MAP_PATH.read_text()).get("pipeline", {})


def load_local_targets(path):
    payload = json.loads(Path(path).read_text())
    if isinstance(payload, dict):
        payload = payload.get("posts", [payload])
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be a list, one object, or an object with posts[]")
    targets = []
    for item in payload:
        if isinstance(item, str):
            targets.append({"record_id": "", "draft_id": "", "status": "", "publish_url": item})
            continue
        if not isinstance(item, dict):
            raise ValueError("Each input item must be a Reddit URL string or object")
        targets.append({
            "record_id": item.get("record_id", ""),
            "draft_id": item.get("draft_id", ""),
            "status": item.get("status", ""),
            "publish_url": item.get("publish_url") or item.get("url") or "",
        })
    return targets


def load_feishu_targets(app_token, table_id, include_all_statuses=False):
    field_map = load_field_map()
    publish_url_field = field_map.get("publish_url", "Publish URL")
    status_field = field_map.get("status", "Status")
    draft_id_field = field_map.get("draft_id", "Draft ID")
    targets = []
    for record in feishu_client.list_records(app_token, table_id):
        fields = record.get("fields", {})
        publish_url = feishu_client.extract_url(fields.get(publish_url_field))
        status = feishu_client.extract_text(fields.get(status_field))
        if not publish_url:
            continue
        if not include_all_statuses and status != "Published":
            continue
        targets.append({
            "record_id": record.get("record_id", ""),
            "draft_id": feishu_client.extract_text(fields.get(draft_id_field)),
            "status": status,
            "publish_url": publish_url,
        })
    return targets


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
    for desired in reddit_post_monitor.monitor_field_defs():
        current = by_name.get(desired["field_name"])
        if not current:
            missing.append(desired)
            continue
        if current.get("type") != desired.get("type"):
            incompatible.append({
                "field": desired["field_name"],
                "existing_type": current.get("type"),
                "required_type": desired.get("type"),
            })
            continue
        wanted = option_names(desired)
        absent = sorted(wanted - option_names(current))
        if absent:
            options_missing.append({"field": desired["field_name"], "options": absent})
    return {"missing": missing, "incompatible": incompatible, "options_missing": options_missing}


def merge_options(current, desired):
    options = list((current.get("property") or {}).get("options", []))
    existing_names = {option.get("name") for option in options}
    for option in (desired.get("property") or {}).get("options", []):
        if option.get("name") not in existing_names:
            options.append(option)
    merged = dict(desired)
    merged["property"] = {"options": options}
    return merged


def ensure_monitor_fields(app_token, table_id, existing_fields, plan):
    if plan["incompatible"]:
        raise RuntimeError(f"Existing monitor fields have incompatible types: {plan['incompatible']}")
    created = []
    updated = []
    by_name = {field.get("field_name"): field for field in existing_fields}
    for desired in plan["missing"]:
        feishu_client.create_field(app_token, table_id, desired)
        created.append(desired["field_name"])
    missing_option_fields = {row["field"] for row in plan["options_missing"]}
    for desired in reddit_post_monitor.monitor_field_defs():
        if desired["field_name"] not in missing_option_fields:
            continue
        current = by_name[desired["field_name"]]
        feishu_client.update_field(
            app_token,
            table_id,
            current["field_id"],
            merge_options(current, desired),
        )
        updated.append(desired["field_name"])
    return created, updated


def load_analysis_overrides(path):
    if not path:
        return {}
    payload = json.loads(Path(path).read_text())
    if isinstance(payload, dict) and "analyses" not in payload:
        return payload
    rows = payload.get("analyses", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Analysis JSON must be a mapping or analyses[] list")
    overrides = {}
    for row in rows:
        key = row.get("record_id") or row.get("publish_url") or row.get("reddit_json_url")
        if not key:
            raise ValueError("Each analysis row needs record_id, publish_url, or reddit_json_url")
        overrides[key] = row
    return overrides


def override_for(target, report, overrides):
    for key in (target.get("record_id"), target.get("publish_url"), report.get("reddit_json_url")):
        if key and key in overrides:
            return overrides[key]
    return None


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
            }
            for target in targets
        ],
        key=lambda target: (
            target["record_id"],
            target["publish_url"],
            target["draft_id"],
        ),
    )


def _snapshot_digest(payload):
    body = dict(payload)
    body.pop("digest", None)
    serialized = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def build_snapshot(targets, reports, plan, include_all_statuses=False, limit_records=0):
    snapshot = {
        "version": SNAPSHOT_VERSION,
        "source": "feishu",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection": {
            "include_all_statuses": bool(include_all_statuses),
            "limit_records": max(0, int(limit_records)),
        },
        "targets": comparable_targets(targets),
        "field_plan": compact_field_plan(plan),
        "reports": reports,
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
        raise ValueError(
            f"Unsupported snapshot version: {snapshot.get('version')!r}"
        )
    if snapshot.get("source") != "feishu":
        raise ValueError("Live updates require a Feishu preview snapshot")
    expected = snapshot.get("digest")
    actual = _snapshot_digest(snapshot)
    if not expected or expected != actual:
        raise ValueError("Snapshot digest mismatch; run a new preview")
    if not isinstance(snapshot.get("reports"), list):
        raise ValueError("Snapshot reports must be a list")
    return snapshot


def validate_snapshot(snapshot, targets, plan, include_all_statuses=False, limit_records=0):
    expected_selection = {
        "include_all_statuses": bool(include_all_statuses),
        "limit_records": max(0, int(limit_records)),
    }
    if snapshot.get("selection") != expected_selection:
        raise ValueError("Snapshot selection does not match the current command")
    if snapshot.get("targets") != comparable_targets(targets):
        raise ValueError("Feishu target rows changed after preview; run a new preview")
    if snapshot.get("field_plan") != compact_field_plan(plan):
        raise ValueError("Feishu monitor field plan changed after preview; run a new preview")
    report_ids = [report.get("record_id", "") for report in snapshot["reports"]]
    target_ids = [target["record_id"] for target in comparable_targets(targets)]
    if sorted(report_ids) != sorted(target_ids) or len(report_ids) != len(set(report_ids)):
        raise ValueError("Snapshot reports do not match the previewed Feishu records")
    for report in snapshot["reports"]:
        if not isinstance(report.get("feishu_patch"), dict):
            raise ValueError("Snapshot report is missing its reviewed Feishu patch")
    return snapshot["reports"]


def load_saved_reddit_payload(directory, resolved_url):
    post_id = reddit_post_monitor.reddit_post_id(resolved_url)
    path = Path(directory) / f"{post_id}.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing saved Reddit JSON: {path}. Open the canonical .json URL in a browser and save it as {post_id}.json"
        )
    return json.loads(path.read_text()), path.name


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-feishu", action="store_true", help="read published rows from Reddit Persona Pipeline")
    source.add_argument("--input-json", help="read Reddit URLs from a local JSON file")
    parser.add_argument("--analysis-json", help="optional reviewed summaries/alerts/signals keyed by record ID or URL")
    parser.add_argument("--reddit-json-dir", help="read browser-saved <post_id>.json payloads instead of making Reddit requests")
    parser.add_argument("--snapshot-out", help="write a successful Feishu dry-run snapshot for later authorized use")
    parser.add_argument("--snapshot-in", help="reuse and verify an approved Feishu preview snapshot; never refetches Reddit")
    parser.add_argument("--include-all-statuses", action="store_true", help="include rows beyond Status=Published")
    parser.add_argument("--ensure-fields", action="store_true", help="preview or create the monitor fields")
    parser.add_argument("--write", action="store_true", help="create missing fields and update Feishu records")
    parser.add_argument("--max-comments", type=int, default=500)
    parser.add_argument("--sample-comments", type=int, default=0)
    parser.add_argument("--limit-records", type=int, default=0)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--user-agent", default=os.environ.get("REDDIT_USER_AGENT", DEFAULT_USER_AGENT))
    args = parser.parse_args()

    if args.write and not args.from_feishu:
        parser.error("--write requires --from-feishu")
    if args.write and not args.snapshot_in:
        parser.error("--write requires --snapshot-in from a reviewed dry-run")
    if args.snapshot_out and not args.from_feishu:
        parser.error("--snapshot-out requires --from-feishu")
    if args.snapshot_out and (args.snapshot_in or args.write):
        parser.error("--snapshot-out cannot be combined with --snapshot-in or --write")
    if args.snapshot_in and (args.analysis_json or args.reddit_json_dir):
        parser.error("--snapshot-in already contains reviewed analysis and cannot be combined with analysis or Reddit payload inputs")

    table_ids = {}
    app_token = ""
    table_id = ""
    existing_fields = []
    plan = {"missing": [], "incompatible": [], "options_missing": []}
    created_fields = []
    updated_fields = []
    write_blocked = False

    needs_feishu = args.from_feishu or args.write or args.ensure_fields
    if needs_feishu:
        table_ids = feishu_client.get_table_ids()
        app_token = table_ids.get("reddit_bitable_app_token") or table_ids.get("bitable_app_token")
        table_id = table_ids.get("reddit_persona_pipeline_table_id")
        if not app_token or not table_id:
            raise RuntimeError("Missing Reddit Persona Pipeline app/table configuration")
        existing_fields = feishu_client.list_fields(app_token, table_id)
        plan = field_plan(existing_fields)

    if args.from_feishu:
        targets = load_feishu_targets(app_token, table_id, args.include_all_statuses)
    else:
        targets = load_local_targets(args.input_json)
    if args.limit_records > 0:
        targets = targets[: args.limit_records]

    overrides = load_analysis_overrides(args.analysis_json)
    reports = []
    errors = []
    updated_records = []
    snapshot_written = ""

    if args.snapshot_in:
        try:
            snapshot = load_snapshot(args.snapshot_in)
            reports = validate_snapshot(
                snapshot,
                targets,
                plan,
                include_all_statuses=args.include_all_statuses,
                limit_records=args.limit_records,
            )
        except Exception as exc:
            errors.append({"stage": "snapshot_validation", "error": str(exc)})

    for index, target in enumerate(targets if not args.snapshot_in else []):
        publish_url = target.get("publish_url", "")
        resolved_url = ""
        json_url = ""
        try:
            resolved_url = reddit_post_monitor.resolve_reddit_permalink(
                publish_url, args.user_agent, timeout=args.timeout
            )
            json_url = reddit_post_monitor.normalize_reddit_json_url(
                resolved_url, limit=args.max_comments
            )
            try:
                payload_source = "network"
                if args.reddit_json_dir:
                    payload, payload_source = load_saved_reddit_payload(
                        args.reddit_json_dir, resolved_url
                    )
                else:
                    payload = reddit_post_monitor.fetch_reddit_json(
                        json_url, args.user_agent, timeout=args.timeout
                    )
                report = reddit_post_monitor.parse_reddit_payload(
                    payload,
                    publish_url,
                    json_url,
                    max_comments=args.max_comments,
                    sample_count=args.sample_comments,
                )
            except reddit_post_monitor.RedditFetchError as exc:
                if exc.status == 404:
                    report = reddit_post_monitor.unavailable_report(
                        publish_url, json_url, status=exc.status
                    )
                else:
                    raise
            report.update({
                "record_id": target.get("record_id", ""),
                "draft_id": target.get("draft_id", ""),
                "current_status": target.get("status", ""),
                "resolved_publish_url": resolved_url,
                "reddit_payload_source": payload_source,
            })
            reddit_post_monitor.apply_analysis_override(
                report, override_for(target, report, overrides)
            )
            report["feishu_patch"] = reddit_post_monitor.build_feishu_patch(report)
            reports.append(report)
        except Exception as exc:
            error = {
                "record_id": target.get("record_id", ""),
                "publish_url": publish_url,
                "error": str(exc),
            }
            if resolved_url:
                error["resolved_publish_url"] = resolved_url
            if json_url:
                error["reddit_json_url"] = json_url
                try:
                    post_id = reddit_post_monitor.reddit_post_id(json_url)
                    error["saved_json_filename"] = f"{post_id}.json"
                except ValueError:
                    pass
            if isinstance(exc, reddit_post_monitor.RedditFetchError) and exc.status in {403, 429}:
                error["recovery"] = (
                    "Reddit blocked this runtime. Open reddit_json_url in a browser, "
                    "save the JSON as saved_json_filename, then rerun with --reddit-json-dir."
                )
            errors.append(error)
        if index + 1 < len(targets) and args.request_delay > 0:
            time.sleep(min(args.request_delay, 10.0))

    if args.snapshot_out and not errors:
        if plan["incompatible"]:
            errors.append({
                "stage": "snapshot_validation",
                "error": f"Monitor field types conflict: {plan['incompatible']}",
            })
        else:
            snapshot_written = save_snapshot(
                args.snapshot_out,
                build_snapshot(
                    targets,
                    reports,
                    plan,
                    include_all_statuses=args.include_all_statuses,
                    limit_records=args.limit_records,
                ),
            )

    if args.write:
        for report in reports:
            if not report.get("record_id"):
                errors.append({
                    "publish_url": report.get("publish_url", ""),
                    "error": "Live Feishu update requires record_id",
                })
        if plan["incompatible"]:
            errors.append({
                "stage": "field_validation",
                "error": f"Monitor field types conflict: {plan['incompatible']}",
            })
        if (plan["missing"] or plan["options_missing"]) and not args.ensure_fields:
            errors.append({
                "stage": "field_validation",
                "error": "Monitor fields are missing; preview and rerun with --ensure-fields --write",
            })
        write_blocked = bool(errors)
        if not write_blocked:
            try:
                if args.ensure_fields:
                    created_fields, updated_fields = ensure_monitor_fields(
                        app_token, table_id, existing_fields, plan
                    )
                for report in reports:
                    record_id = report["record_id"]
                    feishu_client.update_record(
                        app_token, table_id, record_id, report["feishu_patch"]
                    )
                    updated_records.append(record_id)
            except Exception as exc:
                errors.append({"stage": "feishu_write", "error": str(exc)})
                write_blocked = True

    output = {
        "ok": not errors,
        "source": "feishu" if args.from_feishu else str(args.input_json),
        "targets": len(targets),
        "reports": reports,
        "errors": errors,
        "write_requested": args.write,
        "write_blocked": write_blocked,
        "field_plan": compact_field_plan(plan),
        "fields_created": created_fields,
        "fields_updated": updated_fields,
        "records_updated": updated_records,
        "snapshot_used": args.snapshot_in or "",
        "snapshot_written": snapshot_written,
        "downvote_note": "Reddit public JSON does not expose exact downvotes; Downvotes (Estimated) is derived from score and upvote_ratio and remains approximate.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
