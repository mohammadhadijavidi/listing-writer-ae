"""Render assets/hero.png: a real screenshot of the web UI on a bundled SAMPLE property (mock provider).

Requires: pip install playwright && python -m playwright install chromium
Usage:    python docs/render_hero.py [sample-prefix] [out.png] [ar|en]
"""

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sample = sys.argv[1] if len(sys.argv) > 1 else "01"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "assets" / "hero.png"
lang = sys.argv[3] if len(sys.argv) > 3 else "ar"

s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
srv = subprocess.Popen([sys.executable, "-m", "listing_writer_ae", "serve", "--port", str(port), "--provider", "mock"], cwd=ROOT)
for _ in range(50):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1)
        break
    except OSError:
        time.sleep(0.1)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
        page.goto(f"http://127.0.0.1:{port}/?sample={sample}&lang={lang}")
        page.wait_for_selector(".verdict")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)
        page.screenshot(path=str(out))
        browser.close()
finally:
    srv.terminate()
print(f"wrote {out}")
