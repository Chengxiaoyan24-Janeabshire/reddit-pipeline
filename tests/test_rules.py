import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import append_pack
import append_pack_to_feishu
import sync_blog_pool_from_content_all_in_one as pool_sync
import weekly_post_rules


def base_item():
    return {
        "account_code": "R1",
        "content_type": "technical_post",
        "subreddit": "r/Rag",
        "post_type": "Discussion",
        "title": "A focused retrieval tradeoff",
        "body": (
            "I built a small retrieval test around fixed queries and explicit "
            "failure labels. It separates parsing, chunking, filtering, ranking, "
            "and answer synthesis so one change can be evaluated at a time."
        ),
        "disclosure": "",
        "link_policy": "no_link",
        "milvus_mention_basis": "",
        "angle": "retrieval tradeoff",
        "voice_fingerprint": "personal_build_log",
        "length_tier": "short_post",
    }


def errors_for(item):
    errors, warnings = append_pack.validate({"items": [item]})
    return errors, warnings


class PoolSyncRulesTest(unittest.TestCase):
    def test_only_published_blog_post_rows_sync(self):
        published_ms = int(
            datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000
        )
        records = []
        for record_id, category, status, slug in [
            ("rec-published", "Blog Post", "Published", "published"),
            ("rec-posted", "Blog Post", "Posted", "posted"),
            ("rec-planned", "Blog Post", "Planned", "planned"),
            ("rec-other", "Case Study", "Published", "other"),
        ]:
            records.append(
                {
                    "record_id": record_id,
                    "fields": {
                        "Category": category,
                        "Status": status,
                        "Publish URL": f"https://milvus.io/blog/{slug}",
                        "Publish Date": published_ms,
                        "Title & Topic": slug,
                    },
                }
            )

        with mock.patch.object(
            pool_sync.feishu_client, "list_records", return_value=records
        ), mock.patch.object(
            pool_sync.official_blog_catalog, "lookup", return_value=None
        ):
            result = pool_sync.source_candidates(
                "app",
                "table",
                "view",
                catalog={},
                since=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        candidates, unknown, before, non_blog, missing_url, not_published = result
        self.assertEqual([row["record_id"] for row in candidates], ["rec-published"])
        self.assertEqual(not_published, 2)
        self.assertEqual(unknown, [])
        self.assertEqual((before, non_blog, missing_url), (0, 0, 0))


class DraftValidationRulesTest(unittest.TestCase):
    def test_weekly_slots_use_localllama_instead_of_dataengineering(self):
        slots = {
            (slot["account_code"], slot["subreddit"])
            for slot in weekly_post_rules.load_rules()["weekly_slots"]
        }
        self.assertEqual(
            slots,
            {
                ("R1", "r/Rag"),
                ("R1", "r/AI_Agents"),
                ("R2", "r/vectordatabase"),
                ("R2", "r/LocalLLaMA"),
            },
        )
        self.assertNotIn(("R2", "r/dataengineering"), slots)

    def test_localllama_post_types_match_reference_overlays(self):
        slot = weekly_post_rules.slot_for("r/LocalLLaMA")
        self.assertEqual(
            slot["post_types"],
            ["Discussion", "Question | Help", "Resources"],
        )
        self.assertEqual(
            weekly_post_rules.recommend_post_type(
                "r/LocalLLaMA",
                "I need help debugging a local model issue that is not working.",
            ),
            "Question | Help",
        )

    def test_weekly_slot_reference_files_exist(self):
        for slot in weekly_post_rules.load_rules()["weekly_slots"]:
            reference_markdown = ROOT / slot["reference_markdown"]
            self.assertTrue(reference_markdown.is_file(), reference_markdown)
            for screenshot in slot.get("reference_screenshots", []):
                screenshot_path = ROOT / screenshot
                self.assertTrue(screenshot_path.is_file(), screenshot_path)

    def test_weekly_validation_rejects_retired_dataengineering_slot(self):
        expected_specs = [
            {"items": [{"account_code": code, "subreddit": subreddit}]}
            for code, subreddit in [
                ("R1", "r/Rag"),
                ("R1", "r/AI_Agents"),
                ("R2", "r/vectordatabase"),
                ("R2", "r/LocalLLaMA"),
            ]
        ]
        self.assertEqual(append_pack_to_feishu.validate_weekly_specs(expected_specs), [])

        expected_specs[-1]["items"][0]["subreddit"] = "r/dataengineering"
        errors = append_pack_to_feishu.validate_weekly_specs(expected_specs)
        self.assertTrue(any("missing slots" in error for error in errors))
        self.assertTrue(any("unexpected slots" in error for error in errors))

    def test_open_question_is_optional(self):
        declarative = base_item()
        question = copy.deepcopy(declarative)
        question["body"] += " What would you measure next?"

        for item in (declarative, question):
            errors, warnings = errors_for(item)
            self.assertEqual(errors, [])
            self.assertFalse(any("question" in warning.lower() for warning in warnings))

    def test_inferred_short_body_uses_short_post(self):
        item = base_item()
        item.pop("length_tier")
        self.assertEqual(append_pack.infer_length_tier(item), "short_post")

    def test_all_four_length_tiers_exist(self):
        tiers = {
            row["tier"]
            for row in json.loads((ROOT / "data/content_length_rules.json").read_text())
        }
        self.assertEqual(
            tiers,
            {"short_post", "standard_post", "long_post", "code_long_post"},
        )

    def test_i_built_does_not_break_anonymity(self):
        errors, _ = errors_for(base_item())
        self.assertFalse(any("anonymous" in error.lower() for error in errors))

    def test_milvus_in_title_fails(self):
        item = base_item()
        item["title"] = "A Milvus retrieval tradeoff"
        errors, _ = errors_for(item)
        self.assertTrue(any("not the title" in error for error in errors))

    def test_one_supported_milvus_body_mention_passes(self):
        item = base_item()
        item["body"] += " The source uses Milvus for the retrieval layer."
        item["milvus_mention_basis"] = "The source names the retrieval layer."
        errors, _ = errors_for(item)
        self.assertEqual(errors, [])

    def test_two_milvus_body_mentions_fail(self):
        item = base_item()
        item["body"] += " Milvus is used for storage, and Milvus is used for search."
        item["milvus_mention_basis"] = "The source names the storage system."
        errors, _ = errors_for(item)
        self.assertTrue(any("at most 1" in error for error in errors))

    def test_zilliz_fails(self):
        item = base_item()
        item["body"] += " The source also names Zilliz."
        errors, _ = errors_for(item)
        self.assertTrue(any("not allowed to mention Zilliz" in error for error in errors))

    def test_url_fails(self):
        item = base_item()
        item["body"] += " See https://example.com for details."
        errors, _ = errors_for(item)
        self.assertTrue(any("must not contain URLs" in error for error in errors))

    def test_non_no_link_policy_fails(self):
        item = base_item()
        item["link_policy"] = "manual_approved_link"
        errors, _ = errors_for(item)
        self.assertTrue(any("unknown link_policy" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
