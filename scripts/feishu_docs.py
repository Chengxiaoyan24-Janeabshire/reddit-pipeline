#!/usr/bin/env python3
"""Create Feishu Docs for Reddit draft review content."""
import re
import time

import feishu_client

BLOCK_TEXT = 2
BLOCK_H1 = 3
BLOCK_H2 = 4
BLOCK_H3 = 5


def sanitize_title(title, max_len=120):
    text = re.sub(r"\s+", " ", title or "Reddit Drafts").strip()
    text = re.sub(r"[\\/:*\"<>|#%{}]", "-", text)
    return text[:max_len].strip() or "Reddit Drafts"


def parse_inline(text):
    """Convert a small subset of inline markdown into Feishu text runs."""
    elements = []
    pattern = re.compile(
        r"\[(?P<link_text>[^\]]+)\]\((?P<link_url>[^)\s]+)\)"
        r"|(?P<raw_url>https?://[^\s]+)"
        r"|\*\*(?P<bold>[^*]+)\*\*"
        r"|`(?P<code>[^`]+)`"
    )
    last_end = 0
    for match in pattern.finditer(text):
        if match.start() > last_end:
            elements.append({"text_run": {"content": text[last_end:match.start()]}})
        if match.group("link_text"):
            elements.append({
                "text_run": {
                    "content": match.group("link_text"),
                    "text_element_style": {"link": {"url": match.group("link_url")}},
                }
            })
        elif match.group("raw_url"):
            url = match.group("raw_url")
            elements.append({
                "text_run": {
                    "content": url,
                    "text_element_style": {"link": {"url": url}},
                }
            })
        elif match.group("bold"):
            elements.append({
                "text_run": {
                    "content": match.group("bold"),
                    "text_element_style": {"bold": True},
                }
            })
        elif match.group("code"):
            elements.append({
                "text_run": {
                    "content": match.group("code"),
                    "text_element_style": {"inline_code": True},
                }
            })
        last_end = match.end()
    if last_end < len(text):
        elements.append({"text_run": {"content": text[last_end:]}})
    return elements or [{"text_run": {"content": text or ""}}]


def make_text_block(block_type, key, text):
    return {
        "block_type": block_type,
        key: {
            "elements": parse_inline(text),
            "style": {},
        },
    }


def make_code_block(code):
    # Feishu's create-block API is stricter for native code blocks. For review
    # docs, a monospace text block preserves copy/paste behavior reliably.
    return {
        "block_type": BLOCK_TEXT,
        "text": {
            "elements": [
                {
                    "text_run": {
                        "content": code,
                        "text_element_style": {"inline_code": True},
                    }
                }
            ],
            "style": {},
        },
    }


def markdown_to_blocks(markdown):
    blocks = []
    lines = (markdown or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(make_code_block("\n".join(code_lines)))
        elif stripped.startswith("### "):
            blocks.append(make_text_block(BLOCK_H3, "heading3", stripped[4:].strip()))
        elif stripped.startswith("## "):
            blocks.append(make_text_block(BLOCK_H2, "heading2", stripped[3:].strip()))
        elif stripped.startswith("# "):
            blocks.append(make_text_block(BLOCK_H1, "heading1", stripped[2:].strip()))
        elif re.match(r"^[-*] ", stripped):
            blocks.append(make_text_block(BLOCK_TEXT, "text", "• " + stripped[2:].strip()))
        elif re.match(r"^\d+\. ", stripped):
            blocks.append(make_text_block(BLOCK_TEXT, "text", stripped))
        elif stripped == "" or re.match(r"^[-*_]{3,}$", stripped):
            pass
        else:
            blocks.append(make_text_block(BLOCK_TEXT, "text", line))
        i += 1
    return blocks


def create_feishu_doc(folder_token, title):
    token = feishu_client.get_token()
    res = feishu_client.http(
        "POST",
        f"{feishu_client.API_BASE}/docx/v1/documents",
        body={"folder_token": folder_token, "title": sanitize_title(title)},
        token=token,
    )
    if res.get("code") != 0:
        raise RuntimeError(f"Failed to create Feishu doc: {res}")
    return res["data"]["document"]["document_id"]


def write_blocks(document_id, blocks):
    token = feishu_client.get_token()
    url = (
        f"{feishu_client.API_BASE}/docx/v1/documents/{document_id}"
        f"/blocks/{document_id}/children"
    )
    write_index = 0
    for start in range(0, len(blocks), 50):
        batch = blocks[start:start + 50]
        res = feishu_client.http(
            "POST",
            url,
            body={"children": batch, "index": write_index},
            token=token,
        )
        if res.get("code") != 0:
            raise RuntimeError(f"Failed to write Feishu doc blocks: {res}")
        write_index += len(batch)
        if start + 50 < len(blocks):
            time.sleep(0.3)


def replace_blocks(document_id, blocks):
    """Replace all root children in an existing Feishu Doc."""
    token = feishu_client.get_token()
    root_url = (
        f"{feishu_client.API_BASE}/docx/v1/documents/{document_id}"
        f"/blocks/{document_id}"
    )
    root = feishu_client.http("GET", root_url, token=token)
    if root.get("code") != 0:
        raise RuntimeError(f"Failed to read Feishu doc root block: {root}")
    children = (root.get("data", {}).get("block", {}).get("children") or [])
    if children:
        delete_url = root_url + "/children/batch_delete"
        deleted = feishu_client.http(
            "DELETE",
            delete_url,
            body={"start_index": 0, "end_index": len(children)},
            token=token,
        )
        if deleted.get("code") != 0:
            raise RuntimeError(f"Failed to clear Feishu doc blocks: {deleted}")
    if blocks:
        write_blocks(document_id, blocks)


def grant_org_edit_access(document_id):
    token = feishu_client.get_token()
    return feishu_client.http(
        "PATCH",
        f"{feishu_client.API_BASE}/drive/v1/permissions/{document_id}/public?type=docx",
        body={
            "external_access_entity": "open",
            "security_entity": "anyone_can_view",
            "comment_entity": "anyone_can_view",
            "share_entity": "anyone",
            "link_share_entity": "tenant_editable",
        },
        token=token,
    )


def create_doc_from_markdown(title, markdown, folder_token, base_url):
    document_id = create_feishu_doc(folder_token, title)
    blocks = markdown_to_blocks(markdown)
    if blocks:
        write_blocks(document_id, blocks)
    warnings = []
    try:
        permission_res = grant_org_edit_access(document_id)
        if permission_res.get("code") != 0:
            warnings.append(f"doc permission warning: {permission_res}")
    except Exception as exc:
        warnings.append(f"doc permission warning: {exc}")
    doc_url = f"{base_url.rstrip('/')}/docx/{document_id}"
    return doc_url, warnings
