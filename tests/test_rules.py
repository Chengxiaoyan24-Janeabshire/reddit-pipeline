import copy
import json
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import append_pack
import append_pack_to_feishu
import feishu_docs
import render_rule_docs
import resource_paths
import screen_and_assign
import sync_blog_pool_from_content_all_in_one as pool_sync
import weekly_post_rules


def base_item():
    return {
        "account_code": "R1",
        "content_type": "technical_post",
        "subreddit": "r/Rag",
        "post_type": "Discussion",
        "title": "I kept tuning retrieval, but the broken chunks were the problem",
        "body": (
            "I built a small retrieval test around fixed queries and explicit "
            "failure labels. It separates parsing, chunking, filtering, ranking, "
            "and answer synthesis, and I would probably evaluate one change at a time. "
            "The retrieval layer can use vector databases like Milvus."
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
    def test_only_rows_matching_configured_source_contract_sync(self):
        published_ms = int(
            datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000
        )
        valid_category = pool_sync.REQUIRED_CATEGORY
        valid_status = pool_sync.REQUIRED_STATUS
        official_host = pool_sync.SOURCE_RULES["official_hosts"][0]
        path_prefix = pool_sync.REQUIRED_PATH_PREFIX
        records = []
        for record_id, category, status, slug in [
            ("rec-published", valid_category, valid_status, "published"),
            ("rec-posted", valid_category, "Other Status", "posted"),
            ("rec-planned", valid_category, "Future Status", "planned"),
            ("rec-other", "Other Category", valid_status, "other"),
        ]:
            records.append(
                {
                    "record_id": record_id,
                    "fields": {
                        "Category": category,
                        "Status": status,
                        "Publish URL": f"https://{official_host}/{path_prefix}/{slug}",
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
                since=pool_sync.parse_since(pool_sync.DEFAULT_SINCE),
            )

        candidates, unknown, before, non_blog, missing_url, not_published = result
        self.assertEqual([row["record_id"] for row in candidates], ["rec-published"])
        self.assertEqual(not_published, 2)
        self.assertEqual(unknown, [])
        self.assertEqual((before, non_blog, missing_url), (0, 0, 0))

    def test_source_candidates_are_sorted_newest_first(self):
        official_host = pool_sync.SOURCE_RULES["official_hosts"][0]
        path_prefix = pool_sync.REQUIRED_PATH_PREFIX
        records = []
        for record_id, day in [("rec-older", 20), ("rec-newer", 30)]:
            records.append(
                {
                    "record_id": record_id,
                    "fields": {
                        "Category": pool_sync.REQUIRED_CATEGORY,
                        "Status": pool_sync.REQUIRED_STATUS,
                        "Publish URL": f"https://{official_host}/{path_prefix}/{record_id}",
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

    def test_james_luan_articles_follow_normal_minimum_date(self):
        official_host = pool_sync.SOURCE_RULES["official_hosts"][0]
        records = [{
            "record_id": "rec-james",
            "fields": {
                "Category": pool_sync.REQUIRED_CATEGORY,
                "Status": pool_sync.REQUIRED_STATUS,
                "Publish URL": f"https://{official_host}/blog/james-article",
                "Publish Date": int(
                    datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
                ),
                "Title & Topic": "James article",
                "Author": "James Luan",
            },
        }]
        with mock.patch.object(
            pool_sync.feishu_client, "list_records", return_value=records
        ), mock.patch.object(
            pool_sync.official_blog_catalog, "lookup", return_value=None
        ):
            candidates, *_ = pool_sync.source_candidates(
                "app", "table", "view", catalog={},
                since=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        self.assertEqual(candidates, [])


class DraftValidationRulesTest(unittest.TestCase):
    def test_feishu_doc_title_preserves_question_mark(self):
        title = "Would you keep the graph inside the vector DB?"
        self.assertEqual(feishu_docs.sanitize_title(title), title)

    def test_editorial_routes_separate_james_from_anonymous_content(self):
        rules = weekly_post_rules.load_rules()
        self.assertEqual(
            weekly_post_rules.editorial_route_id("jAmEs LuAn", rules),
            "james_luan",
        )
        self.assertEqual(
            weekly_post_rules.editorial_route_id("Other Author", rules),
            "anonymous_default",
        )
        self.assertEqual(
            weekly_post_rules.editorial_route_id("", rules),
            "anonymous_default",
        )
        self.assertTrue(
            weekly_post_rules.source_author_override("James Luan", rules)
        )
        self.assertEqual(
            weekly_post_rules.source_author_override("Other Author", rules),
            {},
        )

    def test_route_specific_reference_and_resource_files_do_not_mix_author_rules(self):
        accounts = json.loads(resource_paths.ACCOUNTS.read_text())
        self.assertEqual(
            [row["account_code"] for row in accounts if "James" in row.get("role", "")],
            ["R3"],
        )
        routing = json.loads(resource_paths.EDITORIAL_ROUTES.read_text())
        for route_id, route in routing["routes"].items():
            reference = json.loads((ROOT / route["reference"]).read_text())
            resource = json.loads((ROOT / route["resource"]).read_text())
            self.assertEqual(reference["route_id"], route_id)
            self.assertEqual(resource["route_id"], route_id)
            self.assertEqual(resource["authority"], "non_authoritative")

    def test_james_r3_modes_keep_distinct_style_and_narrative_contracts(self):
        rules = weekly_post_rules.load_rules()
        james = rules["editorial_routes"]["james_luan"]
        self.assertEqual(james["required_account_code"], "R3")
        modes = james["accounts"]["R3"]["modes"]
        self.assertIn(
            "context_continuity",
            modes["r3_coherent_chapter_rewrite"]["style_contract"],
        )
        self.assertIn(
            "summary_scope",
            modes["r3_article_summary_share"]["style_contract"],
        )
        self.assertNotEqual(
            modes["r3_coherent_chapter_rewrite"]["required_narrative_sequence"],
            modes["r3_article_summary_share"]["required_narrative_sequence"],
        )
        resource = json.loads(
            (ROOT / "resource/reddit/routes/james_luan.json").read_text()
        )
        self.assertEqual(
            set(resource["style_exemplars"]),
            {
                "r3_coherent_chapter_rewrite",
                "r3_article_summary_share",
            },
        )

    def test_generated_james_source_keeps_only_repeatable_chapter_mode(self):
        accounts = json.loads(resource_paths.ACCOUNT_TOPIC_RULES.read_text())
        topics = json.loads(resource_paths.TOPIC_BANK.read_text())
        screened = screen_and_assign.screen_row(
            {
                "blog_id": "source-1",
                "title": "Milvus vector retrieval architecture",
                "url": "https://zilliz.com/blog/example",
                "source_author": "James Luan",
                "generated_count": 1,
            },
            accounts,
            topics,
            top_n=2,
            no_fetch=True,
        )
        modes = screened["assignments"][0]["author_rewrite_modes"]
        self.assertEqual(modes, ["r3_coherent_chapter_rewrite"])

    def test_james_luan_r3_chapter_mode_uses_separate_validation(self):
        rules = weekly_post_rules.load_rules()
        item = base_item()
        item.update({
            "account_code": "R3",
            "subreddit": "r/Rag",
            "voice_fingerprint": "james_author_voice",
            "title": "Vector search grew up and brought an operations manual",
            "body": (
                "Hi, I'm James Luan, CTO of Zilliz, the company and builder behind "
                "Milvus. Milvus is an open-source vector database built to store, "
                "index, and search embeddings. Vector Lakebase is the next step.\n\n"
                "Vector search starts as a neat algorithm and eventually turns into "
                "a real database problem. That is less magical, but much more useful. "
                "We'd love to hear your thoughts."
            ),
            "disclosure": "",
            "milvus_mention_basis": "",
            "author_rewrite_mode": "r3_coherent_chapter_rewrite",
            "link_policy": "no_link",
            "approved_link": "",
            "source_chapter": "Why vector search becomes a database problem",
            "partn": "part1",
        })
        errors, _ = append_pack.validate({
            "source_author": "James Luan",
            "source_url": "https://zilliz.com/blog/example",
            "items": [item],
        })
        self.assertEqual(errors, [])
        item["body"] = "A casual summary without the identity opening."
        errors, _ = append_pack.validate({
            "source_author": "James Luan", "items": [item]
        })
        self.assertTrue(any("disclosed-author opening" in error for error in errors))
        item["body"] = (
            "Hi, I'm James Luan, CTO of Zilliz, the company and builder behind "
            "Milvus. Milvus is an open-source vector database built to store, "
            "index, and search embeddings. Vector Lakebase is the next step.\n\n"
            "A technical summary."
        )
        item["author_rewrite_mode"] = "anonymous_default"
        errors, _ = append_pack.validate({
            "source_author": "James Luan", "items": [item]
        })
        self.assertTrue(any("author_rewrite_mode" in error for error in errors))

    def test_james_r3_chapter_partn_and_share_mode_are_separate(self):
        item = base_item()
        item.update({
            "account_code": "R3",
            "subreddit": "r/Rag",
            "voice_fingerprint": "james_author_voice",
            "title": "Which retrieval boundary becomes the real constraint?",
            "body": (
                "Hi, I'm James Luan, CTO of Zilliz, the company behind Milvus. "
                "Milvus is an open-source vector database designed to store, index, "
                "and search embeddings. Vector Lakebase is the next step.\n\n"
                "This chapter explains one coherent technical boundary."
            ),
            "disclosure": "",
            "milvus_mention_basis": "",
            "author_rewrite_mode": "r3_coherent_chapter_rewrite",
            "link_policy": "no_link",
            "approved_link": "",
            "source_chapter": "One coherent boundary",
            "partn": "Part 1",
        })
        errors, _ = append_pack.validate({
            "source_author": "James Luan",
            "source_url": "https://zilliz.com/blog/example",
            "items": [item],
        })
        self.assertTrue(any("part1, part2" in error for error in errors))

        item["partn"] = "part1"
        errors, _ = append_pack.validate({
            "source_author": "James Luan",
            "source_url": "https://zilliz.com/blog/example",
            "items": [item],
        })
        self.assertEqual(errors, [])

    def test_james_luan_r3_summary_mode_requires_source_link_and_reply_invitation(self):
        source_url = "https://zilliz.com/blog/example"
        item = base_item()
        item.update({
            "account_code": "R3",
            "subreddit": "r/AIMemory",
            "post_type": "Discussion",
            "voice_fingerprint": "james_author_voice",
            "title": "What changes when vector systems reach production?",
            "body": (
                "Hi, I'm James Luan, CTO of Zilliz, the company behind Milvus. "
                "Milvus is an open-source vector database built to store, index, "
                "and search embeddings. Vector Lakebase is the next step.\n\n"
                "The article follows the system from duplicated production data "
                "through freshness boundaries to a lake-native serving direction.\n\n"
                f"I put the full write-up here.\n\n{source_url}\n\n"
                "I'd welcome your thoughts."
            ),
            "disclosure": "",
            "link_policy": "source_link",
            "approved_link": source_url,
            "author_rewrite_mode": "r3_article_summary_share",
            "milvus_mention_basis": "",
        })
        errors, _ = append_pack.validate({
            "source_author": "james luan",
            "source_url": source_url,
            "items": [item],
        })
        self.assertEqual(errors, [])
        item["partn"] = "part1"
        errors, _ = append_pack.validate({
            "source_author": "james luan",
            "source_url": source_url,
            "items": [item],
        })
        self.assertTrue(any("must leave partn empty" in error for error in errors))

    def test_non_james_sources_remain_anonymous_and_no_link(self):
        item = base_item()
        item["disclosure"] = "James Luan"
        errors, _ = append_pack.validate({"source_author": "Other", "items": [item]})
        self.assertTrue(any("anonymous" in error for error in errors))

    def test_inline_source_link_is_not_duplicated_in_final_post(self):
        rendered = append_pack_to_feishu.build_content_markdown({
            "body": "Hi, I'm James, CTO of Zilliz.\n\nhttps://zilliz.com/blog/example",
            "disclosure": "",
            "approved_link": "https://zilliz.com/blog/example",
        })
        self.assertEqual(
            rendered,
            "Hi, I'm James, CTO of Zilliz.\n\n"
            "https://zilliz.com/blog/example\n",
        )

    def test_james_weekly_pack_bypasses_anonymous_r2_question_quota(self):
        specs = [
            {
                "source_author": "James Luan",
                "items": [
                    {"account_code": "R3", "subreddit": "r/Rag", "post_type": "Discussion", "author_rewrite_mode": "r3_article_summary_share"},
                    {"account_code": "R3", "subreddit": "r/AI_Agents", "post_type": "Discussion", "author_rewrite_mode": "r3_coherent_chapter_rewrite"},
                    {"account_code": "R3", "subreddit": "r/AIMemory", "post_type": "Discussion", "author_rewrite_mode": "r3_coherent_chapter_rewrite"},
                ],
            },
            {
                "source_author": "Other",
                "items": [
                    {"account_code": "R2", "subreddit": "r/LocalLLaMA", "post_type": "Question | Help"},
                ],
            },
        ]
        self.assertEqual(append_pack_to_feishu.validate_weekly_specs(specs), [])

        specs[0]["items"][0]["author_rewrite_mode"] = "r3_coherent_chapter_rewrite"
        errors = append_pack_to_feishu.validate_weekly_specs(specs)
        self.assertTrue(any("article_summary_share" in error for error in errors))

    def test_every_future_draft_exposes_original_source_url_in_feishu(self):
        spec = {
            "source_title": "Example",
            "source_url": "https://zilliz.com/blog/example",
            "source_author": "James Luan",
            "items": [base_item()],
        }
        drafts = append_pack_to_feishu.build_drafts(spec, 1, [])
        record = append_pack_to_feishu.build_records(
            spec, drafts, "https://example.feishu.cn/docx/example",
            {"Source Blog URL", "原文"},
        )[0]
        self.assertEqual(record["原文"]["link"], "https://zilliz.com/blog/example")
        anonymous_spec = {
            "source_author": "Other",
            "source_url": "https://zilliz.com/blog/example",
            "items": [base_item()],
        }
        anonymous_drafts = append_pack_to_feishu.build_drafts(anonymous_spec, 1, [])
        anonymous_record = append_pack_to_feishu.build_records(
            anonymous_spec, anonymous_drafts, "https://example.feishu.cn/docx/example",
            {"Source Blog URL", "原文"},
        )[0]
        self.assertEqual(anonymous_record["原文"]["link"], "https://zilliz.com/blog/example")

    def test_checked_in_reference_examples_follow_current_contract(self):
        paths = [
            ROOT / "guidance/reddit/Milvus blog for repurpose.md",
            ROOT / "guidance/reddit/Reddit 内容建议及范例.md",
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
                self.assertEqual(len(append_pack.MILVUS_PATTERN.findall(title)), 0)
                self.assertEqual(len(append_pack.MILVUS_PATTERN.findall(body)), 1)
                self.assertFalse(append_pack.ZILLIZ_PATTERN.search(body))
                self.assertTrue(
                    append_pack.title_has_personal_or_question_perspective(title)
                )
                self.assertTrue(append_pack.has_natural_milvus_context(body))
                self.assertTrue(
                    append_pack.FIRST_PERSON_OPENING_PATTERN.search(
                        append_pack.first_sentence(body)
                    )
                )
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

    def test_weekly_pack_rejects_repeated_surface_scaffold(self):
        specs = json.loads((ROOT / "samples/weekly_pack.example.json").read_text())
        specs[0]["items"][0]["body"] = (
            "I have mixed feelings. " + specs[0]["items"][0]["body"]
        )
        specs[1]["items"][0]["body"] = (
            "I have mixed feelings. " + specs[1]["items"][0]["body"]
        )
        errors = append_pack_to_feishu.validate_weekly_specs(specs)
        self.assertTrue(any("repeats surface scaffold" in error for error in errors))

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

    def test_weekly_sources_use_configured_priority_window_with_fallback(self):
        rules = weekly_post_rules.load_rules()
        policy = rules["source_recency_policy"]
        priority_days = policy["priority_window_days"]
        self.assertGreater(priority_days, 0)
        self.assertTrue(policy["fallback_to_older"])

        as_of = datetime(2026, 8, 4, 12, tzinfo=timezone.utc)
        recent = as_of - timedelta(days=max(0, priority_days - 1))
        older = as_of - timedelta(days=priority_days + 1)
        self.assertTrue(weekly_post_rules.is_recent_source(recent, as_of, rules))
        self.assertFalse(weekly_post_rules.is_recent_source(older, as_of, rules))
        self.assertLess(
            weekly_post_rules.source_priority_key(recent, as_of, rules),
            weekly_post_rules.source_priority_key(older, as_of, rules),
        )

    def test_weekly_slots_match_configured_pack_and_active_accounts(self):
        rules = weekly_post_rules.load_rules()
        slots = rules["weekly_slots"]
        pairs = {(slot["account_code"], slot["subreddit"]) for slot in slots}
        self.assertEqual(len(slots), rules["weekly_pack_size"])
        self.assertEqual(len(pairs), len(slots))
        self.assertTrue(
            {slot["account_code"] for slot in slots}.issubset(
                set(rules["active_accounts"])
            )
        )
        for slot in slots:
            self.assertIn(slot["account_code"], slot["allowed_accounts"])
            self.assertIn("R3", slot["allowed_accounts"])
            self.assertIn(slot["default_post_type"], slot["post_types"])
            self.assertEqual(
                weekly_post_rules.recommend_post_type(slot["subreddit"], "", rules),
                slot["default_post_type"],
            )

    def test_screening_routes_james_only_to_r3(self):
        account_rules = json.loads(resource_paths.ACCOUNT_TOPIC_RULES.read_text())
        self.assertEqual(
            screen_and_assign.eligible_account_codes_for_author(
                "James Luan", account_rules
            ),
            {"R3"},
        )
        self.assertEqual(
            screen_and_assign.eligible_account_codes_for_author(
                "Other Author", account_rules
            ),
            {"R1", "R2"},
        )

    def test_weekly_slot_reference_files_exist(self):
        for slot in weekly_post_rules.load_rules()["weekly_slots"]:
            rule_json = ROOT / slot["rule_json"]
            review_markdown = ROOT / slot["review_markdown"]
            self.assertTrue(rule_json.is_file(), rule_json)
            self.assertTrue(review_markdown.is_file(), review_markdown)
            slot_rule = json.loads(rule_json.read_text())
            self.assertEqual(slot_rule["subreddit"], slot["subreddit"])
            self.assertEqual(
                set(slot_rule["post_type_guidance"]), set(slot["post_types"])
            )
            for screenshot in slot.get("reference_screenshots", []):
                screenshot_path = ROOT / screenshot
                self.assertTrue(screenshot_path.is_file(), screenshot_path)

    def _r2_weekly_specs(self):
        rules = weekly_post_rules.load_rules()
        slots = rules["weekly_slots"]
        specs = [
            {"items": [{"account_code": slot["account_code"], "subreddit": slot["subreddit"]}]}
            for slot in slots
        ]
        question_sub = "r/LocalLLaMA"
        for spec in specs:
            item = spec["items"][0]
            if item["account_code"] == "R2" and item["subreddit"] == question_sub:
                item["post_type"] = weekly_post_rules.r2_question_post_type_for(question_sub, rules)
                item["length_tier"] = "short_post"
                item["title"] = "How do you test this Milvus retrieval tradeoff?"
        return specs

    def test_weekly_validation_requires_one_r2_short_question(self):
        specs = self._r2_weekly_specs()
        self.assertEqual(append_pack_to_feishu.validate_weekly_specs(specs), [])

        # Remove the question Post Type: the pack now has zero R2 question posts.
        for spec in specs:
            item = spec["items"][0]
            if item["account_code"] == "R2" and item["subreddit"] == "r/LocalLLaMA":
                item.pop("post_type")
        errors = append_pack_to_feishu.validate_weekly_specs(specs)
        self.assertTrue(any("exactly one R2 short question post" in e for e in errors))

    def test_weekly_r2_question_must_be_short_post_and_question_title(self):
        specs = self._r2_weekly_specs()
        for spec in specs:
            item = spec["items"][0]
            if item["account_code"] == "R2" and item["subreddit"] == "r/LocalLLaMA":
                item["length_tier"] = "standard_post"
                item["title"] = "A third-person declarative title"
        errors = append_pack_to_feishu.validate_weekly_specs(specs)
        self.assertTrue(any("length_tier 'short_post'" in e for e in errors))
        self.assertTrue(any("explicit question title" in e for e in errors))

    def test_weekly_validation_rejects_unconfigured_slot(self):
        rules = weekly_post_rules.load_rules()
        slots = rules["weekly_slots"]
        expected_specs = [
            {
                "items": [
                    {
                        "account_code": slot["account_code"],
                        "subreddit": slot["subreddit"],
                    }
                ]
            }
            for slot in slots
        ]
        # Mark exactly one R2 slot as the required weekly short question post.
        r2_question_subreddit = "r/LocalLLaMA"
        for spec in expected_specs:
            item = spec["items"][0]
            if item["account_code"] == "R2" and item["subreddit"] == r2_question_subreddit:
                item["post_type"] = weekly_post_rules.r2_question_post_type_for(
                    r2_question_subreddit, rules
                )
                item["length_tier"] = "short_post"
        self.assertEqual(append_pack_to_feishu.validate_weekly_specs(expected_specs), [])

        expected_specs[-1]["items"][0]["subreddit"] = "r/__unexpected__"
        errors = append_pack_to_feishu.validate_weekly_specs(expected_specs)
        self.assertTrue(any("missing subreddit slots" in error for error in errors))
        self.assertTrue(any("unexpected subreddit slots" in error for error in errors))

    def test_discussion_direct_question_gets_soft_close_warning(self):
        declarative = base_item()
        question = copy.deepcopy(declarative)
        question["body"] += " What would you measure next?"

        errors, warnings = errors_for(declarative)
        self.assertEqual(errors, [])
        self.assertFalse(any("interrogative" in warning.lower() for warning in warnings))

        errors, warnings = errors_for(question)
        self.assertEqual(errors, [])
        self.assertFalse(any("asks too many questions" in warning.lower() for warning in warnings))

    def test_discussion_question_pile_warns(self):
        item = base_item()
        item["body"] += (
            " When would you migrate? What failed first? Which system replaced it?"
        )
        errors, warnings = errors_for(item)
        self.assertEqual(errors, [])
        self.assertTrue(any("asks too many questions" in warning.lower() for warning in warnings))

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

    def test_non_first_person_first_sentence_fails(self):
        item = base_item()
        item["body"] = (
            "Most retrieval tests start with fixed queries and explicit labels. "
            "I would probably separate parsing, filtering, ranking, and synthesis. "
            "The retrieval layer can use vector databases like Milvus."
        )
        errors, warnings = errors_for(item)
        self.assertTrue(any("first sentence" in error for error in errors))
        self.assertFalse(any("first-person" in warning for warning in warnings))

    def test_missing_language_buffer_fails(self):
        item = base_item()
        item["body"] = (
            "I built a retrieval test around fixed queries and explicit labels. "
            "It separates parsing, filtering, ranking, and answer synthesis. "
            "The retrieval layer can use vector databases like Milvus."
        )
        errors, warnings = errors_for(item)
        self.assertTrue(any("grammatical language buffer" in error for error in errors))
        self.assertFalse(any("language buffer" in warning for warning in warnings))

    def test_buffer_requirement_follows_guidance_minimum(self):
        item = base_item()
        item["body"] = (
            "I built a retrieval test around fixed queries and explicit labels. "
            "It separates parsing, filtering, ranking, and answer synthesis. "
            "The retrieval layer can use vector databases like Milvus."
        )
        rules = copy.deepcopy(weekly_post_rules.load_rules())
        rules["language_buffer_policy"]["minimum_matches_per_body"] = 0
        with mock.patch.object(
            append_pack.weekly_post_rules, "load_rules", return_value=rules
        ):
            errors, _ = errors_for(item)
        self.assertFalse(any("grammatical language buffer" in error for error in errors))

    def test_ungrammatical_i_concern_does_not_count_as_buffer(self):
        item = base_item()
        item["body"] = (
            "Probably I concern about retrieval drift in this setup. "
            "The pipeline separates parsing, filtering, ranking, and synthesis. "
            "The retrieval layer can use vector databases like Milvus."
        )
        errors, _ = errors_for(item)
        self.assertTrue(any("not a grammatical language buffer" in error for error in errors))

    def test_account_must_use_its_configured_fingerprint(self):
        item = base_item()
        item["voice_fingerprint"] = "structured_design_question"
        errors, _ = errors_for(item)
        self.assertTrue(any("must use voice_fingerprint" in error for error in errors))

    def test_accounts_defer_hard_rules_to_editorial_guidance(self):
        accounts = json.loads(resource_paths.ACCOUNTS.read_text())
        weekly_accounts = weekly_post_rules.load_rules()["account_policies"]
        for account in accounts:
            code = account["account_code"]
            self.assertNotIn("brand_policy", account)
            if code == "R3":
                self.assertEqual(
                    account["hard_rule_authority"],
                    "guidance/reddit/editorial/james_luan_policy.json",
                )
                self.assertTrue(weekly_accounts[code]["may_mention_zilliz"])
            else:
                self.assertEqual(
                    account["hard_rule_authority"],
                    "guidance/reddit/editorial/editorial_policy.json",
                )
                self.assertEqual(weekly_accounts[code]["required_milvus_body_mentions"], 1)
                self.assertFalse(weekly_accounts[code]["may_mention_zilliz"])

        subreddits = json.loads(resource_paths.SUBREDDITS.read_text())
        for subreddit in subreddits:
            self.assertNotIn("account_code", subreddit)
            self.assertNotIn("post_types", subreddit)
            self.assertNotIn("link_policy", subreddit)

    def test_editorial_guidance_merges_with_weekly_workflow(self):
        rules = weekly_post_rules.load_rules()
        self.assertIn("Do not end with a question", rules["post_type_closing_policy"]["Tutorial"])
        self.assertIn("one or two answerable", rules["post_type_closing_policy"]["Discussion"])
        self.assertTrue(
            rules["title_perspective_policy"]["require_first_person_or_question"]
        )
        self.assertEqual(rules["title_hook_policy"]["severity"], "error")
        self.assertEqual(rules["title_hook_policy"]["minimum_signal_groups"], 2)
        self.assertEqual(
            rules["milvus_mention_context_policy"]["mode"],
            "category_example_or_peer_group",
        )
        self.assertEqual(
            rules["opening_perspective_policy"]["scope"], "first_sentence"
        )
        self.assertEqual(rules["opening_perspective_policy"]["severity"], "error")
        self.assertEqual(rules["language_buffer_policy"]["severity"], "error")
        self.assertEqual(
            rules["language_buffer_policy"]["minimum_matches_per_body"], 1
        )

        fingerprints = json.loads(resource_paths.USER_FINGERPRINTS.read_text())
        anonymous = {row["fingerprint_id"]: row for row in fingerprints[:2]}
        for fingerprint_id in ("personal_build_log", "structured_design_question"):
            realization = anonymous[fingerprint_id]["discussion_realization"]
            self.assertEqual(len(realization), 6)
            self.assertTrue(any("threshold" in line.lower() for line in realization))
            opening_spin = anonymous[fingerprint_id]["discussion_opening_spin"]
            self.assertGreaterEqual(len(opening_spin["realizations"]), 6)
            self.assertIn("weekly pack", opening_spin["selection_rule"])
            self.assertTrue(any("mixed feelings" in line.lower() for line in opening_spin["avoid"]))
            structure_spin = anonymous[fingerprint_id]["discussion_structure_spin"]
            self.assertGreaterEqual(len(structure_spin["shapes"]), 6)
            self.assertTrue(any("paragraph" in line.lower() for line in structure_spin["avoid"]))

    def test_instruction_precedence_matches_three_level_contract(self):
        precedence = weekly_post_rules.load_rules()["instruction_precedence"]
        self.assertEqual(precedence["conflict_resolution"], "higher_level_wins")
        self.assertEqual(precedence["unresolvable_conflict"], "reject")
        self.assertEqual(
            [level["id"] for level in precedence["levels"]],
            ["guidance", "subreddit", "audience_angle"],
        )
        self.assertEqual(
            precedence["levels"][0]["controls"],
            ["disclosure", "first_person_language", "language_buffer"],
        )
        self.assertEqual(
            precedence["levels"][1]["controls"],
            [
                "subreddit_subrules",
                "post_category",
                "post_type",
                "native_structure",
                "native_style",
            ],
        )
        self.assertEqual(
            precedence["levels"][2]["controls"],
            ["preferred_technical_angle", "topic_fit", "voice_fingerprint"],
        )

    def test_instruction_precedence_fails_closed_when_reordered(self):
        rules = copy.deepcopy(weekly_post_rules.load_rules())
        rules["instruction_precedence"]["levels"][1:] = reversed(
            rules["instruction_precedence"]["levels"][1:]
        )
        with self.assertRaisesRegex(ValueError, "instruction_precedence level order"):
            weekly_post_rules.validate_contract(rules)

    def test_inferred_short_body_uses_short_post(self):
        item = base_item()
        item.pop("length_tier")
        self.assertEqual(append_pack.infer_length_tier(item), "short_post")

    def test_all_four_length_tiers_exist(self):
        tiers = {
            row["tier"]
            for row in json.loads(resource_paths.CONTENT_LENGTH_RULES.read_text())
        }
        self.assertEqual(
            tiers,
            {"short_post", "standard_post", "long_post", "code_long_post"},
        )

    def test_progressive_resource_layout_is_complete(self):
        self.assertFalse((ROOT / "data").exists())
        self.assertFalse((ROOT / "asset").exists())
        self.assertFalse((resource_paths.REFERENCE_ROOT / "workflow").exists())
        self.assertTrue(resource_paths.RESOURCE_ROOT.is_dir())
        self.assertTrue(resource_paths.RESOURCE_SLOT_ROOT.is_dir())
        self.assertTrue(resource_paths.EDITORIAL_ROOT.is_dir())
        self.assertTrue(resource_paths.WORKFLOW_ROOT.is_dir())
        self.assertEqual(
            resource_paths.EDITORIAL_ROOT,
            resource_paths.GUIDANCE_ROOT / "editorial",
        )
        self.assertEqual(
            resource_paths.WORKFLOW_ROOT,
            resource_paths.GUIDANCE_ROOT / "workflow",
        )
        for path in [
            resource_paths.WEEKLY_WORKFLOW,
            resource_paths.SOURCE_SYNC_RULES,
            resource_paths.EDITORIAL_POLICY,
            resource_paths.EDITORIAL_ROUTES,
            resource_paths.JAMES_LUAN_POLICY,
            resource_paths.CONTENT_LENGTH_RULES,
            resource_paths.ACCOUNTS,
            resource_paths.ACCOUNT_TOPIC_RULES,
            resource_paths.USER_FINGERPRINTS,
            resource_paths.JAMES_LUAN_ACCOUNT_ROUTE,
            resource_paths.ANONYMOUS_ACCOUNT_ROUTE,
            resource_paths.TOPIC_BANK,
            resource_paths.SUBREDDITS,
        ]:
            self.assertTrue(path.is_file(), path)

        for name in [
            "Reddit 运营要求",
            "Reddit 内容问答",
            "Reddit 内容建议及范例",
            "Milvus blog for repurpose",
        ]:
            self.assertTrue((resource_paths.GUIDANCE_ROOT / f"{name}.md").is_file())
            self.assertTrue(
                (resource_paths.RESOURCE_PDF_ROOT / f"{name}.pdf").is_file()
            )

        workflow = json.loads(resource_paths.WEEKLY_WORKFLOW.read_text())
        guidance = json.loads(resource_paths.EDITORIAL_POLICY.read_text())
        self.assertFalse(set(workflow).intersection(guidance))
        self.assertEqual(
            set(weekly_post_rules.load_rules()),
            set(workflow) | set(guidance) | {"editorial_routing", "editorial_routes"},
        )

        rules = weekly_post_rules.load_rules()
        for slot in rules["weekly_slots"]:
            self.assertTrue(slot["rule_json"].startswith("reference/slots/"))
            self.assertTrue(slot["rule_json"].endswith(".json"))
            slot_rule = ROOT / slot["rule_json"]
            self.assertTrue(slot_rule.is_file())
            slot_contract = json.loads(slot_rule.read_text())
            self.assertEqual(
                slot_contract["inherited_contract"]["guidance"],
                "guidance/reddit/editorial/editorial_routes.json",
            )
            self.assertTrue(slot["review_markdown"].startswith("reference/slots/"))
            self.assertTrue(slot["review_markdown"].endswith(".md"))
            slot_markdown = ROOT / slot["review_markdown"]
            self.assertTrue(slot_markdown.is_file())
            slot_text = slot_markdown.read_text()
            self.assertIn("Human review view generated", slot_text)
            self.assertIn(f"Machine source: `{slot['rule_json']}`", slot_text)
            for screenshot in slot["reference_screenshots"]:
                self.assertTrue(screenshot.startswith("resource/reddit/slots/"))
                self.assertTrue((ROOT / screenshot).is_file())

    def test_rule_json_has_current_human_markdown_review(self):
        documents = render_rule_docs.expected_documents()
        self.assertEqual(render_rule_docs.check_documents(documents), [])

        documented_json = {
            source_path
            for _, _, source_paths in render_rule_docs.DOCUMENT_SPECS
            for source_path in source_paths
        }
        rule_json = set((ROOT / "guidance").rglob("*.json")) | set(
            (ROOT / "reference").rglob("*.json")
        )
        self.assertEqual(documented_json, rule_json)

        for output_path, expected in documents.items():
            self.assertTrue(output_path.is_file(), output_path)
            self.assertEqual(output_path.read_text(), expected)
            self.assertIn("Human review view generated", expected)

    def test_merged_contract_fails_closed_on_reference_mismatch(self):
        rules = copy.deepcopy(weekly_post_rules.load_rules())
        rules["weekly_pack_size"] += 1
        with self.assertRaisesRegex(ValueError, "weekly_pack_size"):
            weekly_post_rules.validate_contract(rules)

    def test_slot_machine_rule_must_match_workflow_post_types(self):
        rules = copy.deepcopy(weekly_post_rules.load_rules())
        rules["weekly_slots"][0]["post_types"].append("Unexpected Type")
        with self.assertRaisesRegex(ValueError, "rule_json Post Types"):
            weekly_post_rules.validate_contract(rules)

    def test_i_built_does_not_break_anonymity(self):
        errors, _ = errors_for(base_item())
        self.assertFalse(any("anonymous" in error.lower() for error in errors))

    def test_milvus_in_title_fails(self):
        item = base_item()
        item["title"] = "A Milvus retrieval tradeoff"
        errors, _ = errors_for(item)
        self.assertTrue(any("not the title" in error for error in errors))

    def test_third_person_declarative_title_fails(self):
        item = base_item()
        item["title"] = "A focused retrieval tradeoff"
        errors, _ = errors_for(item)
        self.assertTrue(any("first-person perspective" in error for error in errors))

    def test_first_person_title_passes(self):
        item = base_item()
        item["title"] = "Now I believe freshness matters more than another reranker"
        errors, _ = errors_for(item)
        self.assertEqual(errors, [])

    def test_question_title_passes(self):
        item = base_item()
        item["title"] = "Would you accept more latency just to avoid another retrieval service?"
        errors, _ = errors_for(item)
        self.assertEqual(errors, [])

    def test_generic_topic_question_fails_title_hook_rule(self):
        item = base_item()
        item["title"] = "How should I evaluate retrieval quality?"
        errors, _ = errors_for(item)
        self.assertTrue(any("concrete engineering hook" in error for error in errors))

    def test_viral_title_hook_patterns_are_recognized(self):
        policy = weekly_post_rules.load_rules()["title_hook_policy"]
        titles = [
            "Would you keep the graph inside the vector DB just to avoid running two databases?",
            "The longer an agent runs, the less I care about the prompt",
            "The best local model is usually the wrong question for RAG",
            "Spent 3 weeks blaming our LLM for bad RAG results. It was the vector index.",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(append_pack.title_has_required_hook(title, policy))

    def test_one_supported_milvus_body_mention_passes(self):
        item = base_item()
        errors, _ = errors_for(item)
        self.assertEqual(errors, [])

    def test_direct_milvus_placement_fails(self):
        for direct_sentence in [
            "The retrieval layer can use Milvus.",
            "Milvus handles the retrieval layer.",
            "If Milvus is the retrieval layer, I would log every query.",
        ]:
            with self.subTest(direct_sentence=direct_sentence):
                item = base_item()
                item["body"] = item["body"].replace(
                    "The retrieval layer can use vector databases like Milvus.",
                    direct_sentence,
                )
                errors, _ = errors_for(item)
                self.assertTrue(
                    any("indirect and contextual" in error for error in errors)
                )

    def test_data_infrastructure_example_context_passes(self):
        item = base_item()
        item["body"] = item["body"].replace(
            "vector databases like Milvus", "data infrastructures such as Milvus"
        )
        errors, _ = errors_for(item)
        self.assertEqual(errors, [])

    def test_milvus_and_other_databases_context_passes(self):
        item = base_item()
        item["body"] = item["body"].replace(
            "vector databases like Milvus", "Milvus and other databases"
        )
        errors, _ = errors_for(item)
        self.assertEqual(errors, [])

    def test_zero_milvus_body_mentions_fail(self):
        item = base_item()
        item["body"] = item["body"].replace(
            " The retrieval layer can use vector databases like Milvus.", ""
        )
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

    def test_non_question_post_rejects_named_database_competitor(self):
        item = base_item()
        item["subreddit"] = "r/Rag"
        item["post_type"] = "Discussion"
        item["body"] += " I compared it with Pinecone and Qdrant on the same query set."
        errors, _ = errors_for(item)
        self.assertTrue(any("named database brand" in e for e in errors))

    def test_question_post_allows_named_database_competitor(self):
        item = base_item()
        item["account_code"] = "R2"
        item["subreddit"] = "r/LocalLLaMA"
        item["post_type"] = "Question | Help"
        item["title"] = "How do you compare Milvus against Pinecone for local RAG?"
        item["voice_fingerprint"] = "structured_design_question"
        item["length_tier"] = "short_post"
        item["body"] = (
            "I am trying to decide between self-hosted retrieval options for local RAG. "
            "My current view is that latency and memory fit matter more than a single "
            "benchmark number. When the retrieval layer is a vector database like Milvus, "
            "how do you weigh it against Pinecone for a single-node workload?"
        )
        item["milvus_mention_basis"] = "The source names Milvus as the local retrieval layer."
        errors, _ = errors_for(item)
        self.assertFalse(any("named database brand" in e for e in errors))

    def test_zilliz_fails(self):
        item = base_item()
        item["body"] += " The source also names Zilliz."
        errors, _ = errors_for(item)
        self.assertTrue(any("not allowed to mention Zilliz" in error for error in errors))

    def test_zilliz_in_generated_review_metadata_fails(self):
        item = base_item()
        item["angle"] = "A Zilliz-oriented retrieval angle"
        errors, _ = errors_for(item)
        self.assertTrue(any("not allowed to mention Zilliz" in error for error in errors))

    def test_url_fails(self):
        item = base_item()
        item["body"] += " See https://example.com for details."
        errors, _ = errors_for(item)
        self.assertTrue(any("does not allow URLs" in error for error in errors))

    def test_link_behavior_follows_guidance_mode(self):
        item = base_item()
        item["link_policy"] = "inline_link"
        item["body"] += " See https://example.com for the configured reference."
        rules = copy.deepcopy(weekly_post_rules.load_rules())
        rules["link_policy_modes"]["inline_link"] = {
            "allow_inline_urls": True,
            "allow_approved_link": False,
            "require_approved_link": False,
        }
        rules["account_policies"]["R1"]["link_mode"] = "inline_link"
        rules["account_policies"]["R1"]["default_link_policy"] = "inline_link"
        with mock.patch.object(
            append_pack.weekly_post_rules, "load_rules", return_value=rules
        ):
            errors, _ = errors_for(item)
        self.assertFalse(any("URL" in error for error in errors))

    def test_milvus_title_behavior_follows_guidance(self):
        item = base_item()
        item["title"] = "What I learned about Milvus retrieval tradeoffs"
        rules = copy.deepcopy(weekly_post_rules.load_rules())
        rules["milvus_mention_context_policy"]["allow_in_title"] = True
        with mock.patch.object(
            append_pack.weekly_post_rules, "load_rules", return_value=rules
        ):
            errors, _ = errors_for(item)
        self.assertFalse(any("only in the body" in error for error in errors))

    def test_unconfigured_link_policy_fails(self):
        item = base_item()
        item["link_policy"] = "manual_approved_link"
        errors, _ = errors_for(item)
        self.assertTrue(any("unknown link_policy" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
