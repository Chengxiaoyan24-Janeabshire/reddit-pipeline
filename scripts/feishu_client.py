#!/usr/bin/env python3
"""Small Feishu API helper shared by Reddit pipeline scripts.

Credentials are intentionally not stored in this repo. Resolution order:
  1. FEISHU_CONFIG_PATH
  2. config/feishu-config.json
  3. ~/.codex/feishu_config.json
  4. ~/.claude/feishu_config.json
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://open.feishu.cn/open-apis"
ROOT = Path(__file__).resolve().parents[1]
TABLE_CONFIG = ROOT / "config" / "feishu-tables.json"


def config_path():
    env = os.environ.get("FEISHU_CONFIG_PATH")
    if env:
        return Path(env).expanduser()
    local = ROOT / "config" / "feishu-config.json"
    if local.exists():
        return local
    codex_path = Path.home() / ".codex" / "feishu_config.json"
    if codex_path.exists():
        return codex_path
    claude_path = Path.home() / ".claude" / "feishu_config.json"
    if claude_path.exists():
        return claude_path
    desktop_x_path = Path.home() / "Desktop" / "X Automation" / "feishu-config.json"
    if desktop_x_path.exists():
        return desktop_x_path
    return claude_path


def load_config():
    path = config_path()
    if not path.exists():
        raise FileNotFoundError(
            "Missing Feishu config. Copy config/feishu-config.template.json to "
            "config/feishu-config.json, or set FEISHU_CONFIG_PATH."
        )
    return json.loads(path.read_text()), path


def load_table_config():
    if not TABLE_CONFIG.exists():
        return {}
    return json.loads(TABLE_CONFIG.read_text())


def get_table_ids():
    """Return Reddit table ids from public table config plus optional secret config."""
    cfg, _ = load_config()
    table_cfg = load_table_config()
    merged = dict(cfg)
    merged.update(table_cfg)
    return merged


def http(method, url, body=None, token=None):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read())
        except Exception:
            raise


def get_token():
    cfg, path = load_config()
    now = int(time.time())
    if cfg.get("token") and cfg.get("token_expire_at", 0) > now + 120:
        return cfg["token"]
    res = http(
        "POST",
        f"{API_BASE}/auth/v3/tenant_access_token/internal",
        {"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]},
    )
    if res.get("code") != 0:
        raise RuntimeError(f"Failed to get Feishu token: {res}")
    cfg["token"] = res["tenant_access_token"]
    cfg["token_expire_at"] = now + int(res.get("expire", 7200))
    if path.name == "feishu-config.json":
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
        os.chmod(path, 0o600)
    return cfg["token"]


def extract_text(value):
    if isinstance(value, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in value
        ).strip()
    if isinstance(value, dict):
        return (value.get("text") or value.get("link") or "").strip()
    return str(value).strip() if value is not None else ""


def extract_url(value):
    if isinstance(value, dict):
        return value.get("link") or value.get("text") or ""
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return first.get("link") or first.get("text") or ""
        return str(first)
    return str(value).strip() if value else ""


def list_records(app_token, table_id, page_size=500, view_id=None):
    token = get_token()
    rows = []
    page_token = None
    while True:
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        if view_id:
            params["view_id"] = view_id
        url = (
            f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}"
            f"/records?{urllib.parse.urlencode(params)}"
        )
        res = http("GET", url, token=token)
        if res.get("code") != 0:
            raise RuntimeError(f"Feishu list_records failed: {res}")
        rows.extend(res["data"].get("items", []))
        if not res["data"].get("has_more"):
            break
        page_token = res["data"].get("page_token")
    return rows


def batch_create_records(app_token, table_id, records):
    token = get_token()
    url = f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    body = {"records": [{"fields": r} for r in records]}
    res = http("POST", url, body=body, token=token)
    if res.get("code") != 0:
        raise RuntimeError(f"Feishu batch_create failed: {res}")
    return res


def update_record(app_token, table_id, record_id, fields):
    token = get_token()
    url = f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    res = http("PUT", url, {"fields": fields}, token=token)
    if res.get("code") != 0:
        raise RuntimeError(f"Feishu update_record failed: {res}")
    return res


def list_tables(app_token):
    token = get_token()
    res = http("GET", f"{API_BASE}/bitable/v1/apps/{app_token}/tables?page_size=100", token=token)
    if res.get("code") != 0:
        raise RuntimeError(f"Feishu list_tables failed: {res}")
    return res["data"].get("items", [])


def list_fields(app_token, table_id):
    token = get_token()
    res = http(
        "GET",
        f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields?page_size=100",
        token=token,
    )
    if res.get("code") != 0:
        raise RuntimeError(f"Feishu list_fields failed: {res}")
    return res["data"].get("items", [])


def create_field(app_token, table_id, field):
    token = get_token()
    url = f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    res = http("POST", url, body=field, token=token)
    if res.get("code") != 0:
        raise RuntimeError(f"Feishu create_field failed for {field.get('field_name')}: {res}")
    return res.get("data", {}).get("field") or res.get("data", {})


def update_field(app_token, table_id, field_id, field):
    token = get_token()
    url = f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
    res = http("PUT", url, body=field, token=token)
    if res.get("code") != 0:
        raise RuntimeError(f"Feishu update_field failed for {field.get('field_name')}: {res}")
    return res.get("data", {}).get("field") or res.get("data", {})


def create_table(app_token, name, fields, default_view_name="Grid"):
    token = get_token()
    url = f"{API_BASE}/bitable/v1/apps/{app_token}/tables"
    body = {
        "table": {
            "name": name,
            "default_view_name": default_view_name,
            "fields": fields,
        }
    }
    res = http("POST", url, body=body, token=token)
    if res.get("code") != 0:
        raise RuntimeError(f"Feishu create_table failed for {name}: {res}")
    data = res.get("data", {})
    if "table" in data:
        return data["table"]
    if "table_id" in data:
        return {"name": name, "table_id": data["table_id"]}
    # Some Feishu responses wrap the created table under a singular item-like key.
    for value in data.values():
        if isinstance(value, dict) and value.get("table_id"):
            return value
    raise RuntimeError(f"Feishu create_table returned an unknown shape for {name}: {res}")
