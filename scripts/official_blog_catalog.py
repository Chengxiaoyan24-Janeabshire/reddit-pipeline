#!/usr/bin/env python3
"""Read official blog indexes for title/date enrichment only.

Content All in One / all content remains the source of candidate URLs and dates.
This module canonicalizes URLs and enriches titles/dates from official indexes
when matching metadata is available.
"""
import html as html_module
import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_date(value):
    text = clean_text(value)
    if not text:
        return None
    try:
        iso_text = text[:-1] + "+00:00" if text.endswith("Z") else text
        parsed = datetime.fromisoformat(iso_text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ("%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def fetch_next_data(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    page = response.text
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        page,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Could not find __NEXT_DATA__ on {url}")
    return json.loads(html_module.unescape(match.group(1)))


def canonical_url(url):
    parsed = urlparse((url or "").strip())
    path = re.sub(r"/+$", "", parsed.path)
    return urlunparse((parsed.scheme or "https", parsed.netloc.lower(), path, "", "", ""))


def url_keys(url):
    canonical = canonical_url(url)
    parsed = urlparse(canonical)
    parts = [part for part in parsed.path.split("/") if part]
    keys = {canonical}
    if len(parts) >= 2 and parts[0] in {"blog", "learn"}:
        slug = re.sub(r"\.md$", "", parts[1])
        keys.add(f"slug:{parts[0]}:{slug}")
        keys.add(f"slug:any:{slug}")
    return keys


def crawl_zilliz():
    data = fetch_next_data("https://zilliz.com/blog")
    rows = []
    for item in data.get("props", {}).get("pageProps", {}).get("blogs", []):
        belong = clean_text(item.get("belong") or "blog")
        if belong != "blog":
            continue
        slug = clean_text(item.get("url")).strip("/")
        title = clean_text(item.get("title"))
        if slug and title:
            rows.append({
                "title": title,
                "url": f"https://zilliz.com/blog/{slug}",
                "published_at": parse_date(item.get("display_time")),
            })
    return rows


def crawl_milvus():
    data = fetch_next_data("https://milvus.io/blog")
    rows = []
    for item in data.get("props", {}).get("pageProps", {}).get("blogList", []):
        if item.get("publishToMedium") is False:
            continue
        title = clean_text(item.get("title"))
        href = clean_text(item.get("href"))
        url = clean_text(item.get("origin")) or urljoin("https://milvus.io", href)
        if title and url:
            rows.append({
                "title": title,
                "url": url,
                "published_at": parse_date(item.get("date")),
            })
    return rows


def build_catalog():
    catalog = {}
    for row in crawl_zilliz() + crawl_milvus():
        for key in url_keys(row["url"]):
            catalog[key] = row
    return catalog


def lookup(catalog, url):
    for key in url_keys(url):
        if key in catalog:
            return catalog[key]
    return None


def _find_json_value(value, key):
    if isinstance(value, dict):
        if value.get(key):
            return value[key]
        for child in value.values():
            found = _find_json_value(child, key)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_json_value(child, key)
            if found:
                return found
    return None


def fetch_article_metadata(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    published = None
    title = ""

    for attr, value in (
        ("property", "article:published_time"),
        ("name", "article:published_time"),
        ("name", "date"),
    ):
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            published = parse_date(tag.get("content"))
            if published:
                break

    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = clean_text(og_title.get("content"))

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or script.get_text())
        except (TypeError, json.JSONDecodeError):
            continue
        if not published:
            published = parse_date(_find_json_value(payload, "datePublished"))
        if not title:
            title = clean_text(_find_json_value(payload, "headline"))
        if published and title:
            break

    if not title and soup.title:
        title = clean_text(soup.title.get_text()).split(" | ", 1)[0]
    return {
        "title": title,
        "url": response.url or url,
        "published_at": published,
    }
