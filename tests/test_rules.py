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
import sync_blog_pool_from_content_all_in_one as pool_sync


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
