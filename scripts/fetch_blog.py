#!/usr/bin/env python3
"""Fetch a Milvus/Zilliz blog URL via headless Chromium and print clean text."""
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

CONTENT_SELECTORS = [
    "article",
    "main",
    "[role=main]",
    ".blog-content",
    ".post-content",
    ".article-content",
    "#content",
]

SKIP_HINTS = (
    "logo",
    "icon",
    "avatar",
    "favicon",
    "social",
    "footer",
    "header",
    "nav",
    "pixel",
    "spacer",
)

SYSTEM_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def is_decorative(src, alt):
    haystack = f"{src or ''} {alt or ''}".lower()
    return any(hint in haystack for hint in SKIP_HINTS)


def main():
    if len(sys.argv) < 2:
        print("usage: fetch_blog.py <url> [--images]", file=sys.stderr)
        sys.exit(2)

    url = sys.argv[1]
    with_images = "--images" in sys.argv[2:]

    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if SYSTEM_CHROME.exists():
            launch_kwargs["executable_path"] = str(SYSTEM_CHROME)
        browser = p.chromium.launch(**launch_kwargs)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)

        title = page.title()
        container = None
        container_sel = "body"
        for sel in CONTENT_SELECTORS:
            try:
                loc = page.locator(sel).first
                text = loc.inner_text(timeout=5000)
                if len(text) > 200:
                    container = loc
                    container_sel = sel
                    break
            except Exception:
                continue

        if container is None:
            container = page.locator("body")

        text = container.inner_text(timeout=5000)
        if not with_images:
            browser.close()
            print(f"# {title}\n\n{text}")
            return

        images = []
        for i, img in enumerate(container.locator("img").all()):
            try:
                src = img.get_attribute("src") or ""
                alt = (img.get_attribute("alt") or "").strip()
                if not src or src.startswith("data:"):
                    continue
                src = urljoin(url, src)
                if is_decorative(src, alt):
                    continue
                width = img.evaluate("el => el.naturalWidth || el.width || 0")
                height = img.evaluate("el => el.naturalHeight || el.height || 0")
                if width and width < 200:
                    continue
                images.append({
                    "url": src,
                    "alt": alt,
                    "position": i,
                    "width": width,
                    "height": height,
                })
            except Exception:
                continue

        browser.close()
        print(json.dumps({
            "title": title,
            "text": text,
            "images": images,
            "container_selector": container_sel,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
