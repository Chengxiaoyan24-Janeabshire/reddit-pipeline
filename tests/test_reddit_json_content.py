import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import parse_reddit_json_content
import reddit_json_content
import setup_feishu_tables


def reddit_payload(status_overrides=None, comments=None):
    post = {
        "title": "A local RAG benchmark",
        "author": "example_user",
        "selftext": "Technical details",
        "ups": 120,
        "score": 80,
        "upvote_ratio": 0.8,
        "num_comments": 3,
        "locked": False,
        "archived": False,
        "removed_by_category": None,
    }
    post.update(status_overrides or {})
    comments = comments if comments is not None else [
        "Using Milvus works well here. How does it compare with Qdrant?",
        "Milvus looks broken in this example and the result is misleading.",
        "This feels like a marketing post. Avoid this approach.",
    ]
    comment_nodes = [
        {
            "kind": "t1",
            "data": {
                "body": body,
                "score": 8 - index,
                "depth": 0,
                "replies": "",
            },
        }
        for index, body in enumerate(comments)
    ]
    return [
        {"data": {"children": [{"kind": "t3", "data": post}]}},
        {"data": {"children": comment_nodes}},
    ]


class RedditJsonContentTest(unittest.TestCase):
    def test_decode_plain_and_fenced_json(self):
        payload = reddit_payload()
        raw = json.dumps(payload)
        self.assertEqual(reddit_json_content.decode_json_content(raw), payload)
        self.assertEqual(
            reddit_json_content.decode_json_content(f"```json\n{raw}\n```"),
            payload,
        )

    def test_invalid_json_reports_location(self):
        with self.assertRaisesRegex(ValueError, "line 1, column"):
            reddit_json_content.decode_json_content("[{]")

    def test_parse_metrics_alerts_and_milvus_signals(self):
        report = reddit_json_content.parse_reddit_json_content(
            json.dumps(reddit_payload()),
            publish_url="https://www.reddit.com/r/Rag/comments/abc123/example/",
        )
        self.assertEqual(report["post_status"], "Active")
        self.assertEqual(report["metrics"]["upvotes"], 120)
        self.assertEqual(report["metrics"]["comments"], 3)
        self.assertEqual(report["metrics"]["estimated_downvotes"], 27)
        analysis = report["comment_analysis"]
        self.assertEqual(analysis["public_opinion_alert"], "Alert")
        self.assertIn("Milvus Mention", analysis["milvus_signal"])
        self.assertIn("Milvus Question", analysis["milvus_signal"])
        self.assertIn("Milvus Positive", analysis["milvus_signal"])
        self.assertIn("Milvus Negative", analysis["milvus_signal"])
        self.assertIn("Milvus Comparison", analysis["milvus_signal"])
        self.assertIn("Migration/Adoption", analysis["milvus_signal"])

    def test_one_negative_comment_triggers_watch(self):
        analysis = reddit_json_content.analyze_comments(
            [
                {"body": "The design has a serious problem.", "score": 1},
                {"body": "The rest of the discussion is neutral.", "score": 1},
            ]
        )
        self.assertEqual(analysis["public_opinion_alert"], "Watch")

    def test_removed_post_sets_cancel_patch(self):
        report = reddit_json_content.parse_reddit_payload(
            reddit_payload({"selftext": "[removed]", "removed_by_category": "moderator"})
        )
        patch = reddit_json_content.build_feishu_patch(
            report, updated_at=datetime(2026, 8, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(report["post_status"], "Removed")
        self.assertEqual(patch["Status"], "Cancel")

    def test_deleted_author_does_not_cancel_active_post(self):
        report = reddit_json_content.parse_reddit_payload(
            reddit_payload({"author": "[deleted]", "selftext": "Technical details"})
        )
        self.assertEqual(report["post_status"], "Active")
        self.assertNotIn("Status", reddit_json_content.build_feishu_patch(report))

    def test_patch_never_overwrites_json_inputs(self):
        report = reddit_json_content.parse_reddit_payload(reddit_payload())
        patch = reddit_json_content.build_feishu_patch(report)
        self.assertNotIn("Reddit JSON", patch)
        self.assertNotIn("Reddit JSON Content", patch)

    def test_summary_does_not_copy_comment_text(self):
        analysis = reddit_json_content.analyze_comments(
            [{"body": "plainusername says Milvus is useful for retrieval", "score": 9}]
        )
        self.assertNotIn("plainusername", analysis["comment_summary"])
        self.assertIn("Milvus", analysis["comment_summary"])

    def test_setup_schema_contains_new_json_fields(self):
        fields = {
            field["field_name"]
            for field in setup_feishu_tables.build_schemas()["Reddit Persona Pipeline"]
        }
        self.assertIn("Reddit JSON", fields)
        self.assertIn("Reddit JSON Content", fields)
        self.assertNotIn("Reddit JSON URL", fields)
        self.assertTrue(
            {
                "Upvotes",
                "Comments",
                "Downvotes (Estimated)",
                "Comment Summary",
                "Public Opinion Alert",
                "Milvus Signal",
            }.issubset(fields)
        )

    def test_snapshot_blocks_content_drift(self):
        target = {
            "record_id": "rec_example",
            "draft_id": "draft_example",
            "status": "Published",
            "publish_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
            "reddit_json_content": json.dumps(reddit_payload()),
        }
        report = reddit_json_content.parse_reddit_json_content(
            target["reddit_json_content"], target["publish_url"]
        )
        report.update({key: target[key] for key in ("record_id", "draft_id")})
        report["feishu_patch"] = reddit_json_content.build_feishu_patch(report)
        plan = {"missing": [], "incompatible": [], "options_missing": []}
        snapshot = parse_reddit_json_content.build_snapshot([target], [report], [], plan)
        changed = dict(target, reddit_json_content=json.dumps(reddit_payload({"ups": 121})))
        with self.assertRaisesRegex(ValueError, "Content changed"):
            parse_reddit_json_content.validate_snapshot(snapshot, [changed], plan)

    def test_empty_content_is_waiting_not_error(self):
        target = {
            "record_id": "rec_waiting",
            "draft_id": "draft_waiting",
            "status": "Published",
            "publish_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
            "reddit_json_content": "",
        }
        existing_fields = reddit_json_content.parse_required_field_defs()
        argv = ["parse_reddit_json_content.py", "--from-feishu"]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
            parse_reddit_json_content.feishu_client,
            "get_table_ids",
            return_value={
                "reddit_bitable_app_token": "app",
                "reddit_persona_pipeline_table_id": "table",
            },
        ), mock.patch.object(
            parse_reddit_json_content.feishu_client,
            "list_fields",
            return_value=existing_fields,
        ), mock.patch.object(
            parse_reddit_json_content,
            "load_feishu_targets",
            return_value=[target],
        ), redirect_stdout(io.StringIO()) as output:
            result = parse_reddit_json_content.main()
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["parsed"], 0)
        self.assertEqual(len(payload["waiting_for_content"]), 1)
        self.assertEqual(payload["errors"], [])

    def test_snapshot_write_updates_only_parsed_record(self):
        target = {
            "record_id": "rec_example",
            "draft_id": "draft_example",
            "status": "Published",
            "publish_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
            "reddit_json_content": json.dumps(reddit_payload()),
        }
        report = reddit_json_content.parse_reddit_json_content(
            target["reddit_json_content"], target["publish_url"]
        )
        report.update({key: target[key] for key in ("record_id", "draft_id")})
        report["feishu_patch"] = reddit_json_content.build_feishu_patch(report)
        existing_fields = reddit_json_content.parse_required_field_defs()
        plan = parse_reddit_json_content.field_plan(existing_fields)
        snapshot = parse_reddit_json_content.build_snapshot([target], [report], [], plan)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(snapshot, handle)
            snapshot_path = handle.name
        argv = [
            "parse_reddit_json_content.py",
            "--from-feishu",
            "--snapshot-in",
            snapshot_path,
            "--write",
        ]
        try:
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                parse_reddit_json_content.feishu_client,
                "get_table_ids",
                return_value={
                    "reddit_bitable_app_token": "app",
                    "reddit_persona_pipeline_table_id": "table",
                },
            ), mock.patch.object(
                parse_reddit_json_content.feishu_client,
                "list_fields",
                return_value=existing_fields,
            ), mock.patch.object(
                parse_reddit_json_content,
                "load_feishu_targets",
                return_value=[target],
            ), mock.patch.object(
                parse_reddit_json_content.feishu_client,
                "update_record",
            ) as update_record, redirect_stdout(io.StringIO()) as output:
                result = parse_reddit_json_content.main()
            payload = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["records_updated"], ["rec_example"])
            update_record.assert_called_once()
            patch = update_record.call_args.args[3]
            self.assertNotIn("Reddit JSON", patch)
            self.assertNotIn("Reddit JSON Content", patch)
        finally:
            Path(snapshot_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
