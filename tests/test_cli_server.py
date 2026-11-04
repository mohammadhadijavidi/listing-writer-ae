import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from listing_writer_ae.cli import main
from listing_writer_ae.providers import Mock
from listing_writer_ae.server import list_samples, make_handler


def test_cli_write_sample(capsys):
    rc = main(["write", "04-palm-villa-rent-ar.json", "--provider", "mock"])
    out = capsys.readouterr().out
    assert rc == 0 and "رقم التصريح" in out and "Ready to publish" in out and "Not legal advice" in out


def test_cli_write_not_ready_exit_code(capsys):
    assert main(["write", "02-jvc-studio-rent.json", "--provider", "mock"]) == 1
    assert "LW-P01" in capsys.readouterr().out


def test_cli_write_json_and_file(tmp_path, capsys):
    assert main(["write", "01-marina-2br-sale.json", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["written_by"].startswith("mock") and d["summary"]["error"] == 1
    out = tmp_path / "l.txt"
    main(["write", "01-marina-2br-sale.json", "--lang", "ar", "-o", str(out)])
    assert "شقة" in out.read_text(encoding="utf-8")


def test_cli_check(capsys, tmp_path):
    assert main(["check", "Guaranteed 10% ROI"]) == 1
    assert "LW-C01" in capsys.readouterr().out
    f = tmp_path / "ad.txt"
    f.write_text("شقة جميلة مع شرفة", encoding="utf-8")
    assert main(["check", "-f", str(f), "--lang", "ar"]) == 0


def test_cli_bad_input(capsys, tmp_path):
    assert main(["write", str(tmp_path / "missing.json")]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert main(["write", str(bad)]) == 2


def test_cli_samples_and_sources(capsys):
    assert main(["samples"]) == 0
    assert "01-marina-2br-sale.json" in capsys.readouterr().out
    assert main(["sources"]) == 0
    assert "dubailand.gov.ae" in capsys.readouterr().out


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Mock()))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_server_ui_and_assets(server):
    s, ct, body = _get(server + "/")
    assert s == 200 and "text/html" in ct and b"listing-writer-ae" in body
    s, ct, _ = _get(server + "/fonts/noto-sans-arabic-arabic-400-normal.woff2")
    assert s == 200 and ct == "font/woff2"
    with pytest.raises(urllib.error.HTTPError):
        _get(server + "/fonts/..%2Fserver.py")


def test_server_api(server):
    assert json.loads(_get(server + "/api/health")[2])["mock"] is True
    names = json.loads(_get(server + "/api/samples")[2])["samples"]
    assert names == list_samples()
    prop = json.loads(_get(server + "/api/samples/" + names[0])[2])
    s, d = _post(server + "/api/generate", {"property": prop})
    assert s == 200 and d["title_ar"] and d["findings"] and "ready_to_publish" in d
    s, d = _post(server + "/api/check", {"text": "Best price! Guaranteed ROI"})
    assert s == 200 and d["summary"]["error"] == 1
    assert "rera-circular-2-2022" in json.loads(_get(server + "/api/sources")[2])["sources"]


def test_server_errors(server):
    assert _post(server + "/api/generate", {"property": {"community": "X"}})[0] == 400
    assert _post(server + "/api/check", {"text": ""})[0] == 400
    assert _post(server + "/api/nope", {})[0] == 404
    with pytest.raises(urllib.error.HTTPError):
        _get(server + "/api/samples/../../etc/passwd")
