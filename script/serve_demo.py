"""Local demo server: phuc vu demo_dashboard.html va goi DeepSeek that qua agent, giu API key an toan o server.

Tai sao can server thay vi goi thang tu trinh duyet:
- Neu nhung DeepSeek API key vao file HTML, bat ky ai mo file / xem View Source / DevTools
  deu lay duoc key va co the dung ke, ton tien tai khoan cua ban.
- Server nay giu key trong .env (khong bao gio gui ve trinh duyet), HTML chi goi
  `POST /api/chat` tren cung origin (khong dinh CORS).

Chay:
    uv run python script/serve_demo.py

Sau do mo trinh duyet: http://localhost:8765
"""

from __future__ import annotations

import json
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from core.config import load_settings
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_HTML_PATH = PROJECT_ROOT / "demo_dashboard.html"
PORT = 8765

_settings = None
_agent = None
_index = None


def _ensure_agent():
    """Lazy-build agent + index mot lan duy nhat, dung lai cho moi request."""
    global _settings, _agent, _index
    if _agent is not None:
        return _agent, _index
    _settings = load_settings()
    if not _settings.paths.embeddings_json.exists():
        raise RuntimeError(
            "Chua co embeddings. Chay `uv run python script/run_phase1.py` truoc khi bat server demo."
        )
    _index = LocalEmbeddingIndex.load(_settings)
    _agent = build_agent(_settings, _index)
    return _agent, _index


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - im lang bot log mac dinh cho gon
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - ten ham theo API cua http.server
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/demo_dashboard.html"):
            if not DEMO_HTML_PATH.exists():
                self._send_json(404, {"error": "Khong tim thay demo_dashboard.html"})
                return
            self._send_html(DEMO_HTML_PATH.read_text(encoding="utf-8"))
            return

        # Xem ban ghi goc trong data/clean/papers_clean.json (nguon that cua cau tra loi),
        # thay vi mo trang DOI ben ngoai.
        if parsed.path == "/source":
            paper_id = parse_qs(parsed.query).get("paper_id", [""])[0]
            clean_path = load_settings().paths.clean_json
            records = json.loads(clean_path.read_text(encoding="utf-8"))
            record = next((r for r in records if str(r.get("paper_id")) == paper_id), None)
            if record is None:
                self._send_html(f"<h3>Khong tim thay paper_id: {escape(paper_id)}</h3>")
                return
            pretty = json.dumps(record, ensure_ascii=False, indent=2)
            self._send_html(
                "<!DOCTYPE html><html lang='vi'><head><meta charset='utf-8'>"
                f"<title>Nguon: {escape(paper_id)}</title>"
                "<style>body{font-family:'DM Sans',system-ui,sans-serif;background:#f4f7fe;color:#1b2559;margin:0;padding:28px}"
                ".box{max-width:1000px;margin:0 auto;background:#fff;border-radius:16px;padding:24px;"
                "box-shadow:0 18px 40px rgba(112,144,176,.12)}"
                "h2{margin:0 0 6px;font-size:18px}.p{color:#a3aed0;font-size:12.5px;margin:0 0 18px}"
                "pre{background:#f4f7fe;padding:18px;border-radius:12px;overflow:auto;font-size:12.5px;line-height:1.6}"
                "code{background:#e9edf7;padding:2px 6px;border-radius:5px}</style></head><body><div class='box'>"
                "<h2>Bản ghi nguồn trong dữ liệu đã làm sạch</h2>"
                f"<p class='p'>paper_id: <code>{escape(paper_id)}</code> &nbsp;·&nbsp; File: "
                f"<code>{escape(str(clean_path))}</code> (mở file này trong PyCharm để xem đầy đủ 24 bản ghi)</p>"
                f"<pre>{escape(pretty)}</pre></div></body></html>"
            )
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = str(payload.get("question", "")).strip()
            if not question:
                self._send_json(400, {"error": "Thieu 'question'"})
                return

            agent, index = _ensure_agent()
            answer = run_agent_question(agent, question)

            source = None
            top = index.search(question, top_k=1)
            if top:
                meta = top[0].metadata
                paper_id = str(meta.get("paper_id", ""))
                source = {
                    "title": meta.get("title", top[0].title),
                    "paper_id": paper_id,
                    # Link ve chinh du lieu local (data/clean/papers_clean.json) thay vi trang DOI ben ngoai.
                    "url": f"/source?paper_id={quote(paper_id)}",
                    "doi_url": meta.get("abs_url", ""),
                }

            self._send_json(200, {"answer": answer, "source": source})
        except Exception as exc:  # noqa: BLE001 - tra loi loi ro rang cho demo, khong de server crash
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    print(f"Dang khoi dong agent that (DeepSeek + ChromaDB)...")
    _ensure_agent()
    print(f"San sang. Mo trinh duyet: http://localhost:{PORT}")
    server = ThreadingHTTPServer(("localhost", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDa dung server.")


if __name__ == "__main__":
    main()
