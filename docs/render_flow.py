"""Render assets/flow.png from docs/flow.html (requires Playwright + Chromium)."""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1600, "height": 900})
    page.goto((ROOT / "docs" / "flow.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(300)
    page.screenshot(path=str(ROOT / "assets" / "flow.png"))
    b.close()
print("wrote assets/flow.png")
