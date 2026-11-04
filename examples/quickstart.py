"""Write and check a bilingual listing for a bundled SAMPLE property (offline, mock provider).

    python examples/quickstart.py
    LISTING_PROVIDER=openrouter LISTING_API_KEY=... python examples/quickstart.py   # real model
"""

from pathlib import Path

from listing_writer_ae import Property, write_listing
from listing_writer_ae.generate import render_text

ROOT = Path(__file__).resolve().parent.parent
prop = Property.load(ROOT / "listing_writer_ae" / "samples" / "01-marina-2br-sale.json")
listing = write_listing(prop)  # provider from $LISTING_PROVIDER, default: mock

print(render_text(listing))
print("written by:", listing.written_by, "(SAMPLE data)" if listing.sample else "")
print("kept out of the draft:", listing.dropped_highlights)
for f in listing.findings:
    print(f"{f.severity:7} {f.code} [{f.where}] {f.message_en} {f.match!r}")
print("ready to publish:", listing.ready_to_publish)
