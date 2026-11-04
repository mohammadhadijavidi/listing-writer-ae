"""Command line interface.

  listing-writer-ae write property.json [--provider mock] [--json] [--lang both|ar|en] [-o out.txt]
  listing-writer-ae check "ad text" | -f ad.txt [--property property.json] [--json]
  listing-writer-ae samples
  listing-writer-ae sources
  listing-writer-ae serve [--host 127.0.0.1] [--port 8000] [--provider mock]

Exit codes: 0 ok, 1 errors found (write/check), 2 bad input or provider error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .checks import Finding, check_text, summarise
from .generate import render_text, write_listing
from .providers import PROVIDERS, ProviderError, get_provider
from .schema import Property, PropertyError
from .sources import CHECKED, SOURCES

DISCLAIMER = "Not legal advice. Checks are automated heuristics based on DLD/RERA publications checked on " + CHECKED + "."


def _print_findings(findings: list[Finding], lang: str = "en") -> None:
    if not findings:
        print("No findings.")
        return
    for f in findings:
        msg = f.message_ar if lang == "ar" else f.message_en
        where = f" [{f.where}]" if f.where else ""
        match = f'  "{f.match}"' if f.match else ""
        print(f"{f.severity.upper():7} {f.code}{where}: {msg}{match}")
        if f.sources:
            print("        source: " + ", ".join(f.sources) + "  (see `listing-writer-ae sources`)")


def _resolve_sample(path: str) -> Path:
    p = Path(path)
    if p.exists():
        return p
    from importlib import resources

    cand = resources.files("listing_writer_ae").joinpath("samples", path)
    if cand.is_file():
        return Path(str(cand))
    raise PropertyError(f"{path}: file not found (use `listing-writer-ae samples` to list bundled samples)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="listing-writer-ae", description="Bilingual (Arabic/English) Dubai property listing writer with a claims & compliance checker.")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="generate a listing from property JSON")
    w.add_argument("property", help="path to property JSON (or the name of a bundled sample)")
    w.add_argument("--provider", choices=PROVIDERS, default=None, help="default: $LISTING_PROVIDER or mock")
    w.add_argument("--model", default=None)
    w.add_argument("--lang", choices=["both", "ar", "en"], default="both")
    w.add_argument("--json", action="store_true", help="print the full result as JSON")
    w.add_argument("-o", "--output", help="write the listing text to this file")

    c = sub.add_parser("check", help="check existing ad text for exaggerated claims and missing particulars")
    c.add_argument("text", nargs="?", help="ad text (or use -f)")
    c.add_argument("-f", "--file", help="read ad text from a file ('-' for stdin)")
    c.add_argument("--property", help="property JSON to check consistency and required particulars against")
    c.add_argument("--lang", choices=["en", "ar"], default="en", help="language of the messages")
    c.add_argument("--json", action="store_true")

    sub.add_parser("samples", help="list bundled SAMPLE properties")
    sub.add_parser("sources", help="list the official sources behind the compliance checks")

    s = sub.add_parser("serve", help="start the web UI + JSON API")
    s.add_argument("--host", default=os.getenv("LISTING_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.getenv("LISTING_PORT", "8000")))
    s.add_argument("--provider", choices=PROVIDERS, default=None)
    s.add_argument("--model", default=None)

    a = ap.parse_args(argv)
    try:
        if a.cmd == "write":
            prop = Property.load(_resolve_sample(a.property))
            listing = write_listing(prop, get_provider(a.provider, a.model))
            if a.json:
                print(json.dumps(listing.to_dict(), ensure_ascii=False, indent=2))
            else:
                text = render_text(listing, a.lang)
                if a.output:
                    Path(a.output).write_text(text, encoding="utf-8")
                    print(f"wrote {a.output}")
                else:
                    print(text)
                print(f"--- written by: {listing.written_by}" + ("  (SAMPLE property)" if listing.sample else ""))
                if listing.dropped_highlights:
                    print("--- kept out of the draft (failed claim checks): " + " | ".join(listing.dropped_highlights))
                _print_findings(listing.findings)
                s_ = listing.summary
                verdict = "Ready to publish." if listing.ready_to_publish else "NOT ready to publish."
                if listing.ready_to_publish and s_["error"]:
                    verdict += " (Errors above are in your input notes only; those sentences were kept out of the draft.)"
                print(f"--- {s_['error']} error(s), {s_['warning']} warning(s), {s_['info']} info. {verdict}")
                print(DISCLAIMER)
            return 0 if listing.ready_to_publish else 1
        if a.cmd == "check":
            if a.file:
                text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
            elif a.text:
                text = a.text
            else:
                ap.error("give ad text or -f FILE")
            prop = Property.load(_resolve_sample(a.property)) if a.property else None
            findings = check_text(text, prop)
            if a.json:
                print(json.dumps({"findings": [f.to_dict() for f in findings], "summary": summarise(findings)}, ensure_ascii=False, indent=2))
            else:
                _print_findings(findings, a.lang)
                print(DISCLAIMER)
            return 1 if summarise(findings)["error"] else 0
        if a.cmd == "samples":
            from .server import list_samples

            for n in list_samples():
                print(n)
            return 0
        if a.cmd == "sources":
            print(f"Checked on {CHECKED}. {DISCLAIMER}\n")
            for k, v in SOURCES.items():
                print(f"[{k}] {v['title']}\n    {v['url']}\n    {v['summary']}\n")
            return 0
        if a.cmd == "serve":
            from .server import serve

            serve(a.host, a.port, a.provider, a.model)
            return 0
    except (PropertyError, ProviderError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
