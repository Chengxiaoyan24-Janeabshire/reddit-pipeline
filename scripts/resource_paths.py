#!/usr/bin/env python3
"""Central filesystem locations for Reddit pipeline resources."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RESOURCE_ROOT = ROOT / "resource" / "reddit"
RESOURCE_PDF_ROOT = RESOURCE_ROOT / "pdfs"
RESOURCE_SLOT_ROOT = RESOURCE_ROOT / "slots"

GUIDANCE_ROOT = ROOT / "guidance" / "reddit"
EDITORIAL_ROOT = GUIDANCE_ROOT / "editorial"
EDITORIAL_POLICY = EDITORIAL_ROOT / "editorial_policy.json"
CONTENT_LENGTH_RULES = EDITORIAL_ROOT / "content_length_rules.json"
WORKFLOW_ROOT = GUIDANCE_ROOT / "workflow"
WEEKLY_WORKFLOW = WORKFLOW_ROOT / "weekly.json"
SOURCE_SYNC_RULES = WORKFLOW_ROOT / "source_sync.json"

REFERENCE_ROOT = ROOT / "reference"
ACCOUNT_ROOT = REFERENCE_ROOT / "accounts"
ACCOUNTS = ACCOUNT_ROOT / "accounts.json"
ACCOUNT_TOPIC_RULES = ACCOUNT_ROOT / "account_topic_rules.json"
USER_FINGERPRINTS = ACCOUNT_ROOT / "user_fingerprints.json"
TOPIC_BANK = REFERENCE_ROOT / "topic_bank.json"
SLOT_ROOT = REFERENCE_ROOT / "slots"
SUBREDDITS = SLOT_ROOT / "subreddits.json"
