import copy
import json
import re
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
            "and answer synthesis, and I would probably evaluate one change at a time. "
            "The retrieval layer uses Milvus."
        ),
        "disclosure": "",
        "link_policy": "no_link",
        "milvus_mention_basis": "The source names Milvus as the retrieval layer.",
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

    def test_source_candidates_are_sorted_newest_first(self):
        records = []
        for record_id, day in [("rec-older", 20), ("rec-newer", 30)]:
            records.append(
                {
                    "record_id": record_id,
                    "fields": {
                        "Category": "Blog Post",
                        "Status": "Published",
                        "Publish URL": f"https://milvus.io/blog/{record_id}",
                        "Publish Date": int(
                            datetime(2026, 7, day, tzinfo=timezone.utc).timestamp() * 1000
                        ),
                        "Title & Topic": record_id,
                    },
                }
            )

        with mock.patch.object(
            pool_sync.feishu_client, "list_records", return_value=records
        ), mock.patch.object(
            pool_sync.official_blog_catalog, "lookup", return_value=None
        ):
            candidates, *_ = pool_sync.source_candidates(
                "app",
                "table",
                "view",
                catalog={},
                since=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        self.assertEqual(
            [row["record_id"] for row in candidates],
            ["rec-newer", "rec-older"],
        )


class DraftValidationRulesTest(unittest.TestCase):
    def test_checked_in_reference_examples_follow_current_contract(self):
        paths = [
            ROOT / "reference/Milvus blog for repurpose.md",
            ROOT / "reference/Reddit 内容建议及范例.md",
        ]
        checked = 0
        for path in paths:
            text = path.read_text()
            examples = re.split(r"(?m)^## (?:Example|范例)", text)[1:]
            for example in examples:
                title_match = re.search(
                    r"(?ms)^### Title\s+(.+?)\n\n### Body", example
                )
                body_match = re.search(
                    r"(?ms)^### Body\s+(.+?)(?=\n\n### |\Z)", example
                )
                basis_match = re.search(
                    r"(?ms)^### Milvus mention basis\s+(.+?)(?=\n\n### |\Z)",
                    example,
                )
                self.assertIsNotNone(title_match, path)
                self.assertIsNotNone(body_match, path)
                self.assertIsNotNone(basis_match, path)
                title = title_match.group(1).strip()
                body = body_match.group(1).strip()
                opening = re.split(r"\n\s*\n", body, maxsplit=1)[0]
                self.assertEqual(len(append_pack.MILVUS_PATTERN.findall(title)), 0)
                self.assertEqual(len(append_pack.MILVUS_PATTERN.findall(body)), 1)
                self.assertFalse(append_pack.ZILLIZ_PATTERN.search(body))
                self.assertTrue(append_pack.FIRST_PERSON_OPENING_PATTERN.search(opening))
                if "Question | Help" not in example:
                    self.assertFalse(body.endswith("?"))
                checked += 1
        self.assertEqual(checked, 6)

    def test_checked_in_weekly_sample_satisfies_current_contract(self):
        specs = json.loads((ROOT / "samples/weekly_pack.example.json").read_text())
        self.assertEqual(append_pack_to_feishu.validate_weekly_specs(specs), [])
        for spec in specs:
            errors, warnings = append_pack.validate(spec)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_feishu_date_field_uses_millisecond_timestamp(self):
        self.assertEqual(
            append_pack_to_feishu.feishu_date_value("2026-07-16"),
            int(datetime(2026, 7, 16, tzinfo=timezone.utc).timestamp() * 1000),
        )
        self.assertEqual(
            append_pack_to_feishu.feishu_date_value(1784160000000),
            1784160000000,
        )

    def test_existing_content_doc_url_is_preserved_for_write_recovery(self):
        spec = {
            "items": [
                {
                    **base_item(),
                    "content_doc_url": "https://example.feishu.cn/docx/doc-token",
                }
            ]
        }
        draft = append_pack_to_feishu.build_drafts(spec, 1, [])[0]
        self.assertEqual(
            draft["content_doc_url"],
            "https://example.feishu.cn/docx/doc-token",
        )

    def test_weekly_sources_prioritize_last_seven_days_with_fallback(self):
        rules = weekly_post_rules.load_rules()
        policy = rules["source_recency_policy"]
        self.assertEqual(policy["priority_window_days"], 7)
        self.assertTrue(policy["fallback_to_older"])

        as_of = datetime(2026, 8, 4, 12, tzinfo=timezone.utc)
        recent = datetime(2026, 7, 30, tzinfo=timezone.utc)
        older = datetime(2026, 7, 20, tzinfo=timezone.utc)
        self.assertTrue(weekly_post_rules.is_recent_source(recent, as_of, rules))
        self.assertFalse(weekly_post_rules.is_recent_source(older, as_of, rules))
        self.assertLess(
            weekly_post_rules.source_priority_key(recent, as_of, rules),
            weekly_post_rules.source_priority_key(older, as_of, rules),
        )

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

    def test_discussion_direct_question_gets_soft_close_warning(self):
        declarative = base_item()
        question = copy.deepcopy(declarative)
        question["body"] += " What would you measure next?"

        errors, warnings = errors_for(declarative)
        self.assertEqual(errors, [])
        self.assertFalse(any("interrogative" in warning.lower() for warning in warnings))

        errors, warnings = errors_for(question)
        self.assertEqual(errors, [])
        self.assertTrue(any("interrogative" in warning.lower() for warning in warnings))

    def test_discussion_soft_invitation_avoids_question_warning(self):
        item = base_item()
        item["body"] += (
            " I am curious what others would measure next. "
            "Would love to hear your thoughts."
        )
        errors, warnings = errors_for(item)
        self.assertEqual(errors, [])
        self.assertFalse(any("interrogative" in warning.lower() for warning in warnings))

    def test_tutorial_question_ending_fails(self):
        item = base_item()
        item["post_type"] = "Tutorial"
        item["body"] += " What would you try next?"
        errors, _ = errors_for(item)
        self.assertTrue(any("Tutorial posts must end" in error for error in errors))

    def test_non_first_person_opening_warns(self):
        item = base_item()
        item["body"] = (
            "Most retrieval tests start with fixed queries and explicit labels. "
            "The pipeline separates parsing, filtering, ranking, and synthesis. "
            "The retrieval layer uses Milvus."
        )
        errors, warnings = errors_for(item)
        self.assertEqual(errors, [])
        self.assertTrue(any("first-person" in warning for warning in warnings))

    def test_missing_language_buffer_warns(self):
        item = base_item()
        item["body"] = (
            "I built a retrieval test around fixed queries and explicit labels. "
            "It separates parsing, filtering, ranking, and answer synthesis. "
            "The retrieval layer uses Milvus."
        )
        errors, warnings = errors_for(item)
        self.assertEqual(errors, [])
        self.assertTrue(any("language buffers" in warning for warning in warnings))

    def test_post_type_closing_policy_keeps_fixed_weekly_slots(self):
        rules = weekly_post_rules.load_rules()
        self.assertIn("Do not end with a question", rules["post_type_closing_policy"]["Tutorial"])
        self.assertIn("Would love to hear your thoughts", rules["post_type_closing_policy"]["Discussion"])

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
        errors, _ = errors_for(item)
        self.assertEqual(errors, [])

    def test_zero_milvus_body_mentions_fail(self):
        item = base_item()
        item["body"] = item["body"].replace(" The retrieval layer uses Milvus.", "")
        item["milvus_mention_basis"] = ""
        errors, _ = errors_for(item)
        self.assertTrue(any("exactly once" in error and "found 0" in error for error in errors))

    def test_one_milvus_body_mention_without_basis_fails(self):
        item = base_item()
        item["milvus_mention_basis"] = ""
        errors, _ = errors_for(item)
        self.assertTrue(any("requires milvus_mention_basis" in error for error in errors))

    def test_two_milvus_body_mentions_fail(self):
        item = base_item()
        item["body"] += " Milvus is also used for filtered search."
        item["milvus_mention_basis"] = "The source names the storage system."
        errors, _ = errors_for(item)
        self.assertTrue(any("exactly once" in error and "found 2" in error for error in errors))

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
