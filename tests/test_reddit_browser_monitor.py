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

import reddit_browser_monitor
import setup_feishu_tables


def target(url="https://www.reddit.com/r/Rag/comments/abc123/example/"):
    window = reddit_browser_monitor.monitor_window(
        "2026-08-07T00:00:00+00:00",
        as_of="2026-08-10T00:00:00+00:00",
    )
    return {
        "record_id": "rec_example",
        "draft_id": "RD-EXAMPLE",
        "status": "Published",
        "publish_url": url,
        "canonical_publish_url": reddit_browser_monitor.canonicalize_reddit_url(url),
        **window,
        "monitorable": reddit_browser_monitor.is_reddit_post_url(url),
        "skip_reasons": [],
    }


def observation(**overrides):
    row = {
        "record_id": "rec_example",
        "draft_id": "RD-EXAMPLE",
        "publish_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
        "canonical_url": "https://www.reddit.com/r/Rag/comments/abc123/example/",
        "page_title": "A visible Reddit post",
        "observed_at": "2026-08-07T10:00:00+00:00",
        "upvotes_display": "120",
        "upvotes": 120,
        "upvotes_approximate": False,
        "comments_display": "3",
        "comments": 3,
        "comments_approximate": False,
        "comments_reviewed": 3,
        "comment_sentiments": [
            {
                "sentiment": "Positive",
                "score_display": "25 points",
                "score": 25,
                "score_approximate": False,
                "top_1_percent_commenter": True,
            },
            {
                "sentiment": "Negative",
                "score_display": "-12 points",
                "score": -12,
                "score_approximate": False,
                "top_1_percent_commenter": False,
            },
            {
                "sentiment": "Neutral",
                "score_display": "1 point",
                "score": 1,
                "score_approximate": False,
                "top_1_percent_commenter": False,
            },
        ],
        "comment_summary": "评论主要讨论检索质量，也有人要求补充评测方法。",
        "question_signal": "Yes",
        "negative_signal": "Yes",
        "debate_signal": "Yes",
        "product_signal": "Yes",
        "competitor_signal": "Yes",
        "competitor_mentions": "Pinecone, Qdrant",
        "monitor_status": "Monitored",
        "monitor_notes": "Reviewed all 3 visible comments.",
    }
    row.update(overrides)
    return row


class RedditBrowserMonitorTest(unittest.TestCase):
    def test_visible_count_normalization_marks_rounded_values(self):
        self.assertEqual(reddit_browser_monitor.parse_visible_count("1,234"), (1234, False))
        self.assertEqual(reddit_browser_monitor.parse_visible_count("1.2K"), (1200, True))
        self.assertEqual(reddit_browser_monitor.parse_visible_count("Vote"), (None, False))

    def test_visible_comment_score_supports_negative_and_rounded_scores(self):
        self.assertEqual(
            reddit_browser_monitor.parse_visible_comment_score("-12 points"),
            (-12, False),
        )
        self.assertEqual(
            reddit_browser_monitor.parse_visible_comment_score("1.2K points"),
            (1200, True),
        )
        self.assertEqual(
            reddit_browser_monitor.parse_visible_comment_score("Score hidden"),
            (None, False),
        )

    def test_monitor_windows_prioritize_seven_days_and_stop_after_fourteen(self):
        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)
        self.assertEqual(
            reddit_browser_monitor.monitor_window("2026-08-03", as_of)[
                "monitor_window"
            ],
            "within_7_days",
        )
        self.assertEqual(
            reddit_browser_monitor.monitor_window("2026-08-02", as_of)[
                "monitor_window"
            ],
            "days_8_to_14",
        )
        self.assertTrue(
            reddit_browser_monitor.monitor_window("2026-07-27", as_of)["eligible"]
        )
        self.assertFalse(
            reddit_browser_monitor.monitor_window("2026-07-26", as_of)["eligible"]
        )

    def test_feishu_targets_are_ordered_by_window_and_exclude_older_posts(self):
        as_of = datetime(2026, 8, 10, tzinfo=timezone.utc)

        def published(record_id, day):
            published_ms = int(
                datetime(2026, 8, day, tzinfo=timezone.utc).timestamp() * 1000
            )
            return {
                "record_id": record_id,
                "fields": {
                    "Draft ID": record_id,
                    "Status": "Published",
                    "Publish URL": (
                        f"https://www.reddit.com/r/Rag/comments/{record_id}/example/"
                    ),
                    "Publish Date": published_ms,
                },
            }

        old = {
            "record_id": "old",
            "fields": {
                "Draft ID": "old",
                "Status": "Published",
                "Publish URL": "https://www.reddit.com/r/Rag/comments/old/example/",
                "Publish Date": int(
                    datetime(2026, 7, 20, tzinfo=timezone.utc).timestamp() * 1000
                ),
            },
        }
        with mock.patch.object(
            reddit_browser_monitor.feishu_client,
            "list_records",
            return_value=[published("second", 1), old, published("first", 8)],
        ):
            rows = reddit_browser_monitor.load_feishu_targets(
                "app", "table", as_of=as_of
            )
        monitorable = [row for row in rows if row["monitorable"]]
        self.assertEqual([row["record_id"] for row in monitorable], ["first", "second"])
        self.assertEqual(
            [row["monitor_window"] for row in monitorable],
            ["within_7_days", "days_8_to_14"],
        )
        self.assertFalse(next(row for row in rows if row["record_id"] == "old")["monitorable"])

    def test_only_https_reddit_submission_urls_are_monitorable(self):
        self.assertTrue(
            reddit_browser_monitor.is_reddit_post_url(
                "https://old.reddit.com/r/Rag/comments/abc123/example/?utm_source=x"
            )
        )
        self.assertTrue(reddit_browser_monitor.is_reddit_post_url("https://redd.it/abc123"))
        self.assertTrue(
            reddit_browser_monitor.is_reddit_post_url(
                "https://www.reddit.com/r/Rag/s/QUNOXhSYIY"
            )
        )
        self.assertFalse(reddit_browser_monitor.is_reddit_post_url("http://reddit.com/comments/x"))
        self.assertFalse(reddit_browser_monitor.is_reddit_post_url("https://example.com/post"))

    def test_valid_browser_observation_builds_weighted_sentiment_output(self):
        checked = reddit_browser_monitor.validate_observation(observation(), target())
        patch = reddit_browser_monitor.build_feishu_patch(checked)
        self.assertEqual(patch["Upvotes"], 120)
        self.assertEqual(patch["Comments"], 3)
        self.assertEqual(patch["Comment Sentiment"], "Positive")
        self.assertEqual(checked["comment_sentiment_score"], 0.6)
        self.assertEqual(
            checked["comment_sentiment_summary"]["top_1_percent_comments"], 1
        )
        self.assertEqual(patch["Question Signal"], "Yes")
        self.assertEqual(patch["Negative Signal"], "Yes")
        self.assertEqual(patch["Debate Signal"], "Yes")
        self.assertEqual(patch["Product Signal"], "Yes")
        self.assertEqual(patch["Competitor Signal"], "Yes")
        self.assertEqual(patch["Competitor Mentions"], "Pinecone, Qdrant")
        self.assertNotIn("Impression (7 days)", patch)
        self.assertIn("Comment Summary", patch)
        self.assertNotIn("Status", patch)

    def test_popular_positive_comment_outweighs_an_unweighted_negative_comment(self):
        inputs = [
            reddit_browser_monitor._validate_comment_sentiment_input(
                {
                    "sentiment": "Positive",
                    "score_display": "25 points",
                    "score": 25,
                    "top_1_percent_commenter": False,
                },
                0,
            ),
            reddit_browser_monitor._validate_comment_sentiment_input(
                {
                    "sentiment": "Negative",
                    "score_display": "1 point",
                    "score": 1,
                    "top_1_percent_commenter": False,
                },
                1,
            ),
        ]
        result = reddit_browser_monitor.calculate_comment_sentiment(inputs, 2)
        self.assertEqual(result["positive_comments"], 1)
        self.assertEqual(result["negative_comments"], 1)
        self.assertEqual(result["label"], "Positive")

    def test_heavily_downvoted_negative_comment_counts_as_rejected_negativity(self):
        inputs = [
            reddit_browser_monitor._validate_comment_sentiment_input(
                {
                    "sentiment": "Negative",
                    "score_display": "-100 points",
                    "score": -100,
                    "top_1_percent_commenter": False,
                },
                0,
            )
        ]
        result = reddit_browser_monitor.calculate_comment_sentiment(inputs, 1)
        self.assertEqual(result["label"], "Positive")
        self.assertGreater(result["score"], 0)

    def test_top_one_percent_commenter_adds_stance_weight(self):
        without_badge = [
            reddit_browser_monitor._validate_comment_sentiment_input(
                {
                    "sentiment": "Positive",
                    "score_display": "1 point",
                    "score": 1,
                    "top_1_percent_commenter": False,
                },
                0,
            ),
            reddit_browser_monitor._validate_comment_sentiment_input(
                {
                    "sentiment": "Negative",
                    "score_display": "1 point",
                    "score": 1,
                    "top_1_percent_commenter": False,
                },
                1,
            ),
        ]
        with_badge = [dict(row) for row in without_badge]
        with_badge[1] = reddit_browser_monitor._validate_comment_sentiment_input(
            {
                "sentiment": "Negative",
                "score_display": "1 point",
                "score": 1,
                "top_1_percent_commenter": True,
            },
            1,
        )
        self.assertEqual(
            reddit_browser_monitor.calculate_comment_sentiment(without_badge, 2)[
                "label"
            ],
            "Mixed",
        )
        weighted = reddit_browser_monitor.calculate_comment_sentiment(with_badge, 2)
        self.assertEqual(weighted["label"], "Negative")
        self.assertEqual(weighted["top_1_percent_comments"], 1)

    def test_hidden_comment_score_requires_partial_status(self):
        sentiments = observation()["comment_sentiments"]
        sentiments[0] = {
            "sentiment": "Positive",
            "score_display": "Score hidden",
            "score": None,
            "top_1_percent_commenter": False,
        }
        with self.assertRaisesRegex(ValueError, "comment scores require"):
            reddit_browser_monitor.validate_observation(
                observation(comment_sentiments=sentiments), target()
            )
        checked = reddit_browser_monitor.validate_observation(
            observation(
                comment_sentiments=sentiments,
                monitor_status="Partial",
                monitor_notes="One visible comment score is hidden.",
            ),
            target(),
        )
        self.assertEqual(
            checked["comment_sentiment_summary"]["approximate_or_hidden_scores"],
            1,
        )

    def test_rounded_metric_requires_partial_status(self):
        row = observation(
            upvotes=None,
            upvotes_display="1.2K",
            upvotes_approximate=True,
        )
        with self.assertRaisesRegex(ValueError, "status=Partial"):
            reddit_browser_monitor.validate_observation(row, target())
        checked = reddit_browser_monitor.validate_observation(
            dict(row, monitor_status="Partial", monitor_notes="Upvotes display is rounded."),
            target(),
        )
        self.assertEqual(checked["upvotes"], 1200)

    def test_hidden_metric_requires_partial_status(self):
        row = observation(upvotes=None, upvotes_display="Vote")
        with self.assertRaisesRegex(ValueError, "status=Partial"):
            reddit_browser_monitor.validate_observation(row, target())

    def test_normalized_metrics_must_match_visible_displays(self):
        row = observation(upvotes=121, upvotes_display="120")
        with self.assertRaisesRegex(ValueError, "does not match"):
            reddit_browser_monitor.validate_observation(row, target())

    def test_observed_page_must_match_publish_url(self):
        row = observation(
            canonical_url="https://www.reddit.com/r/Rag/comments/other/wrong/"
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            reddit_browser_monitor.validate_observation(row, target())

    def test_share_url_accepts_same_subreddit_canonical_post(self):
        share_target = target("https://www.reddit.com/r/Rag/s/QUNOXhSYIY")
        row = observation(
            publish_url=share_target["publish_url"],
            canonical_url="https://www.reddit.com/r/Rag/comments/abc123/resolved/",
        )
        checked = reddit_browser_monitor.validate_observation(row, share_target)
        self.assertIn("/comments/abc123/", checked["canonical_url"])

    def test_share_url_rejects_different_subreddit(self):
        share_target = target("https://www.reddit.com/r/Rag/s/QUNOXhSYIY")
        row = observation(
            publish_url=share_target["publish_url"],
            canonical_url="https://www.reddit.com/r/AI_Agents/comments/abc123/wrong/",
        )
        with self.assertRaisesRegex(ValueError, "subreddit does not match"):
            reddit_browser_monitor.validate_observation(row, share_target)

    def test_partial_comment_sample_requires_partial_status(self):
        sentiments = observation()["comment_sentiments"] + [
            {
                "sentiment": "Neutral",
                "score_display": "1 point",
                "score": 1,
                "top_1_percent_commenter": False,
            }
        ]
        row = observation(
            comments=10,
            comments_display="10",
            comments_reviewed=4,
            comment_sentiments=sentiments,
        )
        with self.assertRaisesRegex(ValueError, "partial comment sample"):
            reddit_browser_monitor.validate_observation(row, target())

    def test_reviewed_comments_cannot_exceed_visible_count(self):
        row = observation(comments=2, comments_display="2", comments_reviewed=3)
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            reddit_browser_monitor.validate_observation(row, target())

    def test_raw_comments_and_usernames_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "raw Reddit content"):
            reddit_browser_monitor.validate_observation(
                dict(observation(), raw_comments=["full text"]), target()
            )
        with self.assertRaisesRegex(ValueError, "usernames"):
            reddit_browser_monitor.validate_observation(
                observation(comment_summary="u/example asked a question"), target()
            )

    def test_monitor_summary_preserves_observed_brand_terms(self):
        checked = reddit_browser_monitor.validate_observation(
            observation(comment_summary="评论提到了 Zilliz 和其他数据库。"), target()
        )
        self.assertIn("Zilliz", checked["comment_summary"])

    def test_competitor_signal_requires_named_or_described_mentions(self):
        with self.assertRaisesRegex(ValueError, "competitor_mentions is required"):
            reddit_browser_monitor.validate_observation(
                observation(competitor_mentions=""), target()
            )
        with self.assertRaisesRegex(ValueError, "must be empty"):
            reddit_browser_monitor.validate_observation(
                observation(competitor_signal="None"), target()
            )

    def test_signals_require_reviewed_comments(self):
        row = observation(
            comments=0,
            comments_display="0",
            comments_reviewed=0,
            comment_sentiments=[],
            comment_summary="当前没有可分析的评论。",
        )
        with self.assertRaisesRegex(ValueError, "require at least one reviewed comment"):
            reddit_browser_monitor.validate_observation(row, target())

    def test_schema_retires_json_and_exposes_browser_monitor_fields(self):
        fields = {
            field["field_name"]
            for field in setup_feishu_tables.build_schemas()["Reddit Persona Pipeline"]
        }
        self.assertNotIn("Reddit JSON", fields)
        self.assertNotIn("Reddit JSON Content", fields)
        self.assertNotIn("Downvotes (Estimated)", fields)
        self.assertNotIn("Upvote Ratio", fields)
        self.assertTrue(
            {
                "Upvotes",
                "Comments",
                "Comment Summary",
                "Comment Sentiment",
                "Question Signal",
                "Negative Signal",
                "Debate Signal",
                "Product Signal",
                "Competitor Signal",
                "Competitor Mentions",
                "Impression (7 days)",
                "Reddit Monitor Status",
                "Reddit Monitor Notes",
            }.issubset(fields)
        )

    def test_signal_field_options_are_replaced_with_yes_and_none(self):
        fields = reddit_browser_monitor.monitor_field_defs()
        question = next(
            field for field in fields if field["field_name"] == "Question Signal"
        )
        question["field_id"] = "fld_question"
        question["property"] = {
            "options": [{"name": "None"}, {"name": "Review"}, {"name": "Respond"}]
        }
        plan = reddit_browser_monitor.field_plan(fields)
        self.assertEqual(plan["options_missing"][0]["field"], "Question Signal")
        with mock.patch.object(
            reddit_browser_monitor.feishu_client, "update_field"
        ) as update_field:
            created, updated = reddit_browser_monitor.ensure_monitor_fields(
                "app", "table", fields, plan
            )
        self.assertEqual(created, [])
        self.assertEqual(updated, ["Question Signal"])
        desired = update_field.call_args.args[3]
        self.assertEqual(
            {option["name"] for option in desired["property"]["options"]},
            {"None", "Yes"},
        )

    def test_snapshot_blocks_publish_url_drift(self):
        current_target = target()
        checked = reddit_browser_monitor.validate_observation(observation(), current_target)
        checked["feishu_patch"] = reddit_browser_monitor.build_feishu_patch(checked)
        plan = {"missing": [], "incompatible": [], "options_missing": []}
        snapshot = reddit_browser_monitor.build_snapshot(
            [current_target], [checked], plan
        )
        changed = target("https://www.reddit.com/r/Rag/comments/def456/changed/")
        with self.assertRaisesRegex(ValueError, "Publish URLs.*changed"):
            reddit_browser_monitor.validate_snapshot(snapshot, [changed], plan)

    def test_snapshot_blocks_publish_date_or_monitor_window_drift(self):
        current_target = target()
        checked = reddit_browser_monitor.validate_observation(observation(), current_target)
        checked["feishu_patch"] = reddit_browser_monitor.build_feishu_patch(checked)
        plan = {"missing": [], "incompatible": [], "options_missing": []}
        snapshot = reddit_browser_monitor.build_snapshot(
            [current_target], [checked], plan
        )
        changed = dict(current_target)
        changed.update(
            reddit_browser_monitor.monitor_window(
                "2026-07-27T00:00:00+00:00",
                as_of="2026-08-10T00:00:00+00:00",
            )
        )
        changed["monitorable"] = True
        with self.assertRaisesRegex(ValueError, "Publish Dates.*changed"):
            reddit_browser_monitor.validate_snapshot(snapshot, [changed], plan)

    def test_snapshot_write_updates_only_reviewed_record(self):
        current_target = target()
        checked = reddit_browser_monitor.validate_observation(observation(), current_target)
        checked["feishu_patch"] = reddit_browser_monitor.build_feishu_patch(checked)
        fields = reddit_browser_monitor.monitor_field_defs()
        plan = reddit_browser_monitor.field_plan(fields)
        snapshot = reddit_browser_monitor.build_snapshot(
            [current_target], [checked], plan
        )
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(snapshot, handle)
            snapshot_path = handle.name
        argv = [
            "reddit_browser_monitor.py",
            "--snapshot-in",
            snapshot_path,
            "--write",
        ]
        try:
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                reddit_browser_monitor,
                "_table_config",
                return_value=("app", "table"),
            ), mock.patch.object(
                reddit_browser_monitor,
                "load_feishu_targets",
                return_value=[current_target],
            ), mock.patch.object(
                reddit_browser_monitor.feishu_client,
                "list_fields",
                return_value=fields,
            ), mock.patch.object(
                reddit_browser_monitor.feishu_client,
                "update_record",
            ) as update_record, redirect_stdout(io.StringIO()) as output:
                result = reddit_browser_monitor.main()
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
