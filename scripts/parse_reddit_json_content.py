#!/usr/bin/env python3
"""Preview or write metrics parsed from Feishu Reddit JSON Content fields."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import feishu_client
import reddit_json_content


ROOT = Path(__file__).resolve().parents[1]
FIELD_MAP_PATH = ROOT / "config" / "feishu-fields.json"
SNAPSHOT_VERSION = 1


def load_field_map():
    if not FIELD_MAP_PATH.exists():
        return {}
    return json.loads(FIELD_MAP_PATH.read_text()).get("pipeline", {})


def content_digest(content):
    return hashlib.sha256(str(content or "").encode("utf-8")).hexdigest()


def load_feishu_targets(app_token, table_id, include_all_statuses=False):
    field_map = load_field_map()
    draft_id_field = field_map.get("draft_id", "Draft ID")
    status_field = field_map.get("status", "Status")
    publish_url_field = field_map.get("publish_url", "Publish URL")
    content_field = field_map.get("reddit_json_content", "Reddit JSON Content")
    targets = []
    for record in feishu_client.list_records(app_token, table_id):
        fields = record.get("fields", {})
        status = feishu_client.extract_text(fields.get(status_field))
        if not include_all_statuses and status != "Published":
            continue
        targets.append(
            {
                "record_id": record.get("record_id", ""),
                "draft_id": feishu_client.extract_text(fields.get(draft_id_field)),
                "status": status,
                "publish_url": feishu_client.extract_url(fields.get(publish_url_field)),
                "reddit_json_content": feishu_client.extract_text(fields.get(content_field)),
            }
        )
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
    for desired in reddit_json_content.parse_required_field_defs():
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
        absent = sorted(option_names(desired) - option_names(current))
        if absent:
            options_missing.append({"field": desired["field_name"], "options": absent})
    return {
        "missing": missing,
        "incompatible": incompatible,
        "options_missing": options_missing,
    }


def merge_options(current, desired):
    options = list((current.get("property") or {}).get("options", []))
    existing_names = {option.get("name") for option in options}
    for option in (desired.get("property") or {}).get("options", []):
        if option.get("name") not in existing_names:
            options.append(option)
    merged = dict(desired)
    merged["property"] = {"options": options}
    return merged


def ensure_parse_fields(app_token, table_id, existing_fields, plan):
    if plan["incompatible"]:
        raise RuntimeError(f"Existing parse fields have incompatible types: {plan['incompatible']}")
    created = []
    updated = []
    by_name = {field.get("field_name"): field for field in existing_fields}
    for desired in plan["missing"]:
        feishu_client.create_field(app_token, table_id, desired)
        created.append(desired["field_name"])
    option_fields = {row["field"] for row in plan["options_missing"]}
    for desired in reddit_json_content.parse_required_field_defs():
        if desired["field_name"] not in option_fields:
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
                "content_length": len(target.get("reddit_json_content", "")),
                "content_sha256": content_digest(target.get("reddit_json_content", "")),
            }
            for target in targets
        ],
        key=lambda target: (target["record_id"], target["draft_id"]),
    )


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
        if not isinstance(row, dict):
            raise ValueError("Each analysis row must be an object")
        key = row.get("record_id") or row.get("draft_id") or row.get("publish_url")
        if not key:
            raise ValueError("Each analysis row needs record_id, draft_id, or publish_url")
        overrides[key] = row
    return overrides


def override_for(target, overrides):
    for key in (target.get("record_id"), target.get("draft_id"), target.get("publish_url")):
        if key and key in overrides:
            return overrides[key]
    return None


def _snapshot_digest(payload):
    body = dict(payload)
    body.pop("digest", None)
    serialized = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def build_snapshot(targets, reports, waiting, plan, include_all_statuses=False):
    snapshot = {
        "version": SNAPSHOT_VERSION,
        "source": "feishu_reddit_json_content",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection": {"include_all_statuses": bool(include_all_statuses)},
        "targets": comparable_targets(targets),
        "field_plan": compact_field_plan(plan),
        "reports": reports,
        "waiting": waiting,
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
    if snapshot.get("source") != "feishu_reddit_json_content":
        raise ValueError("Live updates require a Reddit JSON Content preview snapshot")
    expected = snapshot.get("digest")
    actual = _snapshot_digest(snapshot)
    if not expected or expected != actual:
        raise ValueError("Snapshot digest mismatch; run a new preview")
    if not isinstance(snapshot.get("reports"), list):
        raise ValueError("Snapshot reports must be a list")
    return snapshot


def validate_snapshot(snapshot, targets, plan, include_all_statuses=False):
    expected_selection = {"include_all_statuses": bool(include_all_statuses)}
    if snapshot.get("selection") != expected_selection:
        raise ValueError("Snapshot selection does not match the current command")
    if snapshot.get("targets") != comparable_targets(targets):
        raise ValueError("Feishu target rows or Reddit JSON Content changed after preview; run a new preview")
    if snapshot.get("field_plan") != compact_field_plan(plan):
        raise ValueError("Feishu parse field plan changed after preview; run a new preview")
    target_ids = {target.get("record_id", "") for target in targets}
    report_ids = [report.get("record_id", "") for report in snapshot["reports"]]
    if len(report_ids) != len(set(report_ids)) or any(record_id not in target_ids for record_id in report_ids):
        raise ValueError("Snapshot reports do not match the previewed Feishu records")
    for report in snapshot["reports"]:
        if not isinstance(report.get("feishu_patch"), dict):
            raise ValueError("Snapshot report is missing its reviewed Feishu patch")
    return snapshot["reports"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-feishu", action="store_true", required=True)
    parser.add_argument("--analysis-json", help="optional reviewed summaries/alerts/signals keyed by record, draft, or publish URL")
    parser.add_argument("--snapshot-out", help="write a successful dry-run snapshot for later authorized use")
    parser.add_argument("--snapshot-in", help="reuse and verify an approved preview snapshot")
    parser.add_argument("--include-all-statuses", action="store_true")
    parser.add_argument("--ensure-fields", action="store_true", help="create missing output fields during an authorized write")
    parser.add_argument("--write", action="store_true", help="update Feishu from an approved snapshot")
    parser.add_argument("--max-comments", type=int, default=500)
    parser.add_argument("--sample-comments", type=int, default=0)
    args = parser.parse_args()

    if args.write and not args.snapshot_in:
        parser.error("--write requires --snapshot-in from a reviewed dry-run")
    if args.snapshot_out and (args.snapshot_in or args.write):
        parser.error("--snapshot-out cannot be combined with --snapshot-in or --write")
    if args.snapshot_in and args.analysis_json:
        parser.error("--snapshot-in already contains reviewed analysis")

    table_ids = feishu_client.get_table_ids()
    app_token = table_ids.get("reddit_bitable_app_token") or table_ids.get("bitable_app_token")
    table_id = table_ids.get("reddit_persona_pipeline_table_id")
    if not app_token or not table_id:
        raise RuntimeError("Missing Reddit Persona Pipeline app/table configuration")

    existing_fields = feishu_client.list_fields(app_token, table_id)
    plan = field_plan(existing_fields)
    targets = load_feishu_targets(app_token, table_id, args.include_all_statuses)
    overrides = load_analysis_overrides(args.analysis_json)
    reports = []
    waiting = []
    errors = []
    created_fields = []
    updated_fields = []
    updated_records = []
    snapshot_written = ""
    write_blocked = False

    if args.snapshot_in:
        try:
            snapshot = load_snapshot(args.snapshot_in)
            reports = validate_snapshot(
                snapshot,
                targets,
                plan,
                include_all_statuses=args.include_all_statuses,
            )
            waiting = snapshot.get("waiting", [])
        except Exception as exc:
            errors.append({"stage": "snapshot_validation", "error": str(exc)})
    else:
        for target in targets:
            content = target.get("reddit_json_content", "")
            if not content.strip():
                waiting.append(
                    {
                        "record_id": target.get("record_id", ""),
                        "draft_id": target.get("draft_id", ""),
                        "reason": "Reddit JSON Content is empty",
                    }
                )
                continue
            try:
                report = reddit_json_content.parse_reddit_json_content(
                    content,
                    publish_url=target.get("publish_url", ""),
                    max_comments=args.max_comments,
                    sample_count=args.sample_comments,
                )
                report.update(
                    {
                        "record_id": target.get("record_id", ""),
                        "draft_id": target.get("draft_id", ""),
                        "current_status": target.get("status", ""),
                        "reddit_json_content_length": len(content),
                        "reddit_json_content_sha256": content_digest(content),
                    }
                )
                reddit_json_content.apply_analysis_override(report, override_for(target, overrides))
                report["feishu_patch"] = reddit_json_content.build_feishu_patch(report)
                reports.append(report)
            except Exception as exc:
                errors.append(
                    {
                        "record_id": target.get("record_id", ""),
                        "draft_id": target.get("draft_id", ""),
                        "error": str(exc),
                    }
                )

    if args.snapshot_out and not errors:
        if plan["incompatible"]:
            errors.append(
                {
                    "stage": "snapshot_validation",
                    "error": f"Parse field types conflict: {plan['incompatible']}",
                }
            )
        else:
            snapshot_written = save_snapshot(
                args.snapshot_out,
                build_snapshot(
                    targets,
                    reports,
                    waiting,
                    plan,
                    include_all_statuses=args.include_all_statuses,
                ),
            )

    if args.write:
        if plan["incompatible"]:
            errors.append(
                {
                    "stage": "field_validation",
                    "error": f"Parse field types conflict: {plan['incompatible']}",
                }
            )
        if (plan["missing"] or plan["options_missing"]) and not args.ensure_fields:
            errors.append(
                {
                    "stage": "field_validation",
                    "error": "Parse fields are missing; rerun the approved snapshot with --ensure-fields --write",
                }
            )
        write_blocked = bool(errors)
        if not write_blocked:
            try:
                if args.ensure_fields:
                    created_fields, updated_fields = ensure_parse_fields(
                        app_token, table_id, existing_fields, plan
                    )
                for report in reports:
                    record_id = report.get("record_id", "")
                    if not record_id:
                        raise ValueError("Live Feishu update requires record_id")
                    feishu_client.update_record(app_token, table_id, record_id, report["feishu_patch"])
                    updated_records.append(record_id)
            except Exception as exc:
                errors.append({"stage": "feishu_write", "error": str(exc)})
                write_blocked = True

    output = {
        "ok": not errors,
        "source": "feishu_reddit_json_content",
        "targets": len(targets),
        "parsed": len(reports),
        "waiting_for_content": waiting,
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
        "network_note": "This command never requests Reddit; it parses only Feishu Reddit JSON Content.",
        "downvote_note": "Reddit does not expose exact public downvotes; Downvotes (Estimated) is derived from score and upvote_ratio.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
