import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import reddit_post_monitor
import setup_feishu_tables
import sync_reddit_post_metrics


def reddit_payload(status_overrides=None):
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
    comments = [
        {
            "kind": "t1",
            "data": {
                "body": "Using Milvus works well here. How does it compare with Qdrant?",
                "score": 8,
                "depth": 0,
                "replies": "",
            },
        },
        {
            "kind": "t1",
            "data": {
                "body": "Milvus looks broken in this example and the result is misleading.",
                "score": 5,
                "depth": 0,
                "replies": "",
            },
        },
        {
            "kind": "t1",
            "data": {
                "body": "This feels like a marketing post. Avoid this approach.",
                "score": 3,
                "depth": 0,
                "replies": "",
            },
        },
    ]
    return [
        {"data": {"children": [{"kind": "t3", "data": post}]}},
        {"data": {"children": comments}},
    ]


class RedditPostMonitorTest(unittest.TestCase):
    def test_normalize_reddit_json_url(self):
        url = "https://www.reddit.com/r/Rag/comments/abc123/example/?utm_source=test"
        normalized = reddit_post_monitor.normalize_reddit_json_url(url, limit=200)
        self.assertEqual(
            normalized,
            "https://www.reddit.com/r/Rag/comments/abc123/example.json?raw_json=1&limit=200&sort=top",
        )

    def test_reddit_url_requires_https_submission_path(self):
        with self.assertRaises(ValueError):
            reddit_post_monitor.normalize_reddit_json_url(
                "http://www.reddit.com/r/Rag/comments/abc123/example/"
            )
        with self.assertRaises(ValueError):
            reddit_post_monitor.normalize_reddit_json_url(
                "https://www.reddit.com/r/Rag/"
            )

    def test_comment_text_removes_usernames_and_links(self):
        sanitized = reddit_post_monitor.sanitize_comment_text(
            "u/example and @another shared https://example.com/details"
        )
        self.assertEqual(sanitized, "[user] and [user] shared [link]")

    def test_share_url_resolves_before_json_suffix(self):
        share_url = "https://www.reddit.com/r/Rag/s/shareToken"
        canonical = "https://www.reddit.com/r/Rag/comments/abc123/example/?share_id=tracking"

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def geturl(self):
                return canonical

        with mock.patch.object(
            reddit_post_monitor.urllib.request, "urlopen", return_value=Response()
        ):
            resolved = reddit_post_monitor.resolve_reddit_permalink(
                share_url, "test-agent"
            )
        self.assertEqual(
            resolved,
            "https://www.reddit.com/r/Rag/comments/abc123/example/",
        )
        self.assertEqual(
            reddit_post_monitor.normalize_reddit_json_url(resolved),
            "https://www.reddit.com/r/Rag/comments/abc123/example.json?raw_json=1&limit=500&sort=top",
        )

    def test_parse_metrics_alerts_and_milvus_signals(self):
        publish_url = "https://www.reddit.com/r/Rag/comments/abc123/example/"
        json_url = reddit_post_monitor.normalize_reddit_json_url(publish_url)
        report = reddit_post_monitor.parse_reddit_payload(
            reddit_payload(), publish_url, json_url
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

    def test_removed_post_sets_cancel_patch(self):
        publish_url = "https://www.reddit.com/r/Rag/comments/abc123/example/"
        json_url = reddit_post_monitor.normalize_reddit_json_url(publish_url)
        report = reddit_post_monitor.parse_reddit_payload(
            reddit_payload({"selftext": "[removed]", "removed_by_category": "moderator"}),
            publish_url,
            json_url,
        )
        patch = reddit_post_monitor.build_feishu_patch(
            report, updated_at=datetime(2026, 8, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(report["post_status"], "Removed")
        self.assertEqual(patch["Status"], "Cancel")

    def test_deleted_author_does_not_cancel_active_post(self):
        publish_url = "https://www.reddit.com/r/Rag/comments/abc123/example/"
        json_url = reddit_post_monitor.normalize_reddit_json_url(publish_url)
        report = reddit_post_monitor.parse_reddit_payload(
            reddit_payload({"author": "[deleted]", "selftext": "Technical details"}),
            publish_url,
            json_url,
        )
        self.assertEqual(report["post_status"], "Active")
        self.assertNotIn("Status", reddit_post_monitor.build_feishu_patch(report))

    def test_unavailable_does_not_set_cancel(self):
        publish_url = "https://www.reddit.com/r/Rag/comments/missing/example/"
        json_url = reddit_post_monitor.normalize_reddit_json_url(publish_url)
        report = reddit_post_monitor.unavailable_report(publish_url, json_url)
        patch = reddit_post_monitor.build_feishu_patch(report)
        self.assertEqual(report["post_status"], "Unavailable")
        self.assertEqual(report["comment_analysis"]["public_opinion_alert"], "None")
        self.assertNotIn("Status", patch)

    def test_analysis_override_is_validated(self):
        report = reddit_post_monitor.unavailable_report(
            "https://reddit.com/comments/example",
            "https://reddit.com/comments/example.json?raw_json=1&limit=500&sort=top",
        )
        reddit_post_monitor.apply_analysis_override(report, {
            "comment_summary": "A reviewed summary from u/example at https://example.com.",
            "public_opinion_alert": "None",
            "milvus_signal": ["Milvus Mention"],
        })
        self.assertEqual(
            report["comment_analysis"]["comment_summary"],
            "A reviewed summary from [user] at [link]",
        )
        with self.assertRaises(ValueError):
            reddit_post_monitor.apply_analysis_override(
                report, {"public_opinion_alert": "Negative"}
            )

    def test_heuristic_summary_does_not_copy_comment_text(self):
        analysis = reddit_post_monitor.analyze_comments([
            {"body": "plainusername says Milvus is useful for retrieval", "score": 9},
        ])
        self.assertNotIn("plainusername", analysis["comment_summary"])
        self.assertIn("Milvus", analysis["comment_summary"])

    def test_setup_schema_contains_monitor_fields(self):
        fields = {
            field["field_name"]
            for field in setup_feishu_tables.build_schemas()["Reddit Persona Pipeline"]
        }
        self.assertTrue({
            "Upvotes",
            "Comments",
            "Downvotes (Estimated)",
            "Comment Summary",
            "Public Opinion Alert",
            "Milvus Signal",
        }.issubset(fields))

    def test_live_write_rejects_local_input(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump([{
                "record_id": "rec_example",
                "publish_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
            }], handle)
            input_path = handle.name
        argv = [
            "sync_reddit_post_metrics.py",
            "--input-json",
            input_path,
            "--write",
        ]
        try:
            with mock.patch.object(sys, "argv", argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    sync_reddit_post_metrics.main()
            self.assertEqual(raised.exception.code, 2)
        finally:
            Path(input_path).unlink(missing_ok=True)

    def test_snapshot_blocks_target_drift(self):
        target = {
            "record_id": "rec_example",
            "draft_id": "draft_example",
            "status": "Published",
            "publish_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
        }
        report = reddit_post_monitor.parse_reddit_payload(
            reddit_payload(),
            target["publish_url"],
            reddit_post_monitor.normalize_reddit_json_url(target["publish_url"]),
        )
        report.update(target)
        report["feishu_patch"] = reddit_post_monitor.build_feishu_patch(report)
        plan = {"missing": [], "incompatible": [], "options_missing": []}
        snapshot = sync_reddit_post_metrics.build_snapshot([target], [report], plan)
        changed = dict(target, publish_url="https://www.reddit.com/r/Rag/comments/changed/example/")
        with self.assertRaisesRegex(ValueError, "target rows changed"):
            sync_reddit_post_metrics.validate_snapshot(snapshot, [changed], plan)

    def test_browser_saved_reddit_json_fallback(self):
        resolved_url = "https://www.reddit.com/r/Rag/comments/abc123/example/"
        with tempfile.TemporaryDirectory() as directory:
            payload_path = Path(directory) / "abc123.json"
            payload_path.write_text(json.dumps(reddit_payload()))
            payload, filename = sync_reddit_post_metrics.load_saved_reddit_payload(
                directory, resolved_url
            )
        self.assertEqual(filename, "abc123.json")
        self.assertEqual(payload[0]["data"]["children"][0]["data"]["title"], "A local RAG benchmark")

    def test_snapshot_write_does_not_refetch_reddit(self):
        target = {
            "record_id": "rec_example",
            "draft_id": "draft_example",
            "status": "Published",
            "publish_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
        }
        report = reddit_post_monitor.parse_reddit_payload(
            reddit_payload(),
            target["publish_url"],
            reddit_post_monitor.normalize_reddit_json_url(target["publish_url"]),
        )
        report.update(target)
        report["feishu_patch"] = reddit_post_monitor.build_feishu_patch(report)
        existing_fields = reddit_post_monitor.monitor_field_defs()
        plan = sync_reddit_post_metrics.field_plan(existing_fields)
        snapshot = sync_reddit_post_metrics.build_snapshot([target], [report], plan)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(snapshot, handle)
            snapshot_path = handle.name
        argv = [
            "sync_reddit_post_metrics.py",
            "--from-feishu",
            "--snapshot-in",
            snapshot_path,
            "--write",
        ]
        try:
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                sync_reddit_post_metrics.feishu_client,
                "get_table_ids",
                return_value={
                    "reddit_bitable_app_token": "app",
                    "reddit_persona_pipeline_table_id": "table",
                },
            ), mock.patch.object(
                sync_reddit_post_metrics.feishu_client,
                "list_fields",
                return_value=existing_fields,
            ), mock.patch.object(
                sync_reddit_post_metrics,
                "load_feishu_targets",
                return_value=[target],
            ), mock.patch.object(
                sync_reddit_post_metrics.reddit_post_monitor,
                "fetch_reddit_json",
            ) as fetch_reddit, mock.patch.object(
                sync_reddit_post_metrics.feishu_client,
                "update_record",
            ) as update_record, redirect_stdout(io.StringIO()) as output:
                result = sync_reddit_post_metrics.main()
            payload = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["records_updated"], ["rec_example"])
            fetch_reddit.assert_not_called()
            update_record.assert_called_once()
        finally:
            Path(snapshot_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
