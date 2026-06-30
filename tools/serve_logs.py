#!/usr/bin/env python3
"""serve_logs.py — Browse experiment logs over HTTP.

Serves the logs directory as static files (so the ``*.html`` timelines and
``*-routes.pdf`` render natively in the browser) and adds a generated dashboard
at ``/`` that groups every experiment run with one-click links to its timeline,
final report, transcript, routes PDF, and per-host logs/reports.

Runs are discovered the same way the other tools cluster them: each run writes a
``{run_stem}-final-report.md``, so the run stem identifies the run and its
sibling artifacts (``{run_stem}.html``, ``{run_stem}.txt``,
``{run_stem}-routes.pdf``, ``{run_stem}-{host}.log``, ...).

Usage:
    python tools/serve_logs.py                 # serve <repo>/logs on 127.0.0.1:8000
    python tools/serve_logs.py --port 9000
    python tools/serve_logs.py --logs-dir path/to/logs --host 0.0.0.0
"""

import argparse
import html
import json
import sys
from collections import defaultdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent

FINAL_SUFFIX = "-final-report.md"
HOST_REPORT_SUFFIX = "-report.md"

# Suffixes we serve inline as UTF-8 text so they render in the browser instead of
# triggering a download.
INLINE_TEXT_SUFFIXES = {".md", ".log", ".txt", ".json", ".csv"}


def discover_runs(logs_dir: Path) -> dict[str, list[dict]]:
    """Map a category (logs-relative parent dir) -> list of run descriptors.

    Each run descriptor has: stem, report, html, txt, pdf, hosts (host ->
    {"log": Path|None, "report": Path|None}).
    """
    runs_by_category: dict[str, list[dict]] = defaultdict(list)

    # Group final reports by their directory so per-host files can be attributed
    # to the most specific run stem when one stem is a prefix of another.
    stems_by_dir: dict[Path, list[str]] = defaultdict(list)
    for fr in logs_dir.rglob("*" + FINAL_SUFFIX):
        stems_by_dir[fr.parent].append(fr.name[: -len(FINAL_SUFFIX)])

    for d, stems in stems_by_dir.items():
        stems_sorted = sorted(stems, key=len, reverse=True)

        # Attribute each non-final file in the directory to its run stem.
        hosts_by_stem: dict[str, dict[str, dict]] = defaultdict(dict)
        for f in d.glob("*"):
            if not f.is_file() or f.name.endswith(FINAL_SUFFIX):
                continue
            for stem in stems_sorted:
                if not f.name.startswith(stem):
                    continue
                rest = f.name[len(stem):]
                if f.suffix == ".log" and rest.startswith("-"):
                    host = rest[1:-len(".log")]
                    hosts_by_stem[stem].setdefault(host, {})["log"] = f
                elif rest.endswith(HOST_REPORT_SUFFIX) and rest.startswith("-"):
                    host = rest[1:-len(HOST_REPORT_SUFFIX)]
                    hosts_by_stem[stem].setdefault(host, {})["report"] = f
                break

        category = str(d.relative_to(logs_dir))
        for stem in sorted(stems):
            def sibling(suffix: str) -> Path | None:
                p = d / f"{stem}{suffix}"
                return p if p.exists() else None

            hosts = {h: {"log": v.get("log"), "report": v.get("report")}
                     for h, v in sorted(hosts_by_stem.get(stem, {}).items())}
            runs_by_category[category].append({
                "stem": stem,
                "report": d / f"{stem}{FINAL_SUFFIX}",
                "html": sibling(".html"),
                "txt": sibling(".txt"),
                "pdf": sibling("-routes.pdf"),
                "hosts": hosts,
            })

    return runs_by_category


def _url(logs_dir: Path, path: Path) -> str:
    return "/" + quote(str(path.relative_to(logs_dir)))


def _link(logs_dir: Path, path: Path | None, label: str) -> str:
    if path is None:
        return f'<span class="missing">{html.escape(label)}</span>'
    return f'<a href="{_url(logs_dir, path)}">{html.escape(label)}</a>'


def render_dashboard(logs_dir: Path) -> bytes:
    runs_by_category = discover_runs(logs_dir)
    total_runs = sum(len(v) for v in runs_by_category.values())

    parts: list[str] = [_PAGE_HEAD.format(
        n_runs=total_runs, n_cats=len(runs_by_category),
        root=html.escape(str(logs_dir)))]

    if not runs_by_category:
        parts.append(f'<p class="missing">No runs (*{FINAL_SUFFIX}) found under '
                     f'{html.escape(str(logs_dir))}.</p>')

    for category in sorted(runs_by_category):
        runs = runs_by_category[category]
        parts.append(f'<section><h2>{html.escape(category)} '
                     f'<span class="count">({len(runs)})</span></h2>')
        for run in runs:
            search = html.escape(f"{category} {run['stem']} "
                                 f"{' '.join(run['hosts'])}".lower())
            links = " &middot; ".join([
                _link(logs_dir, run["html"], "timeline"),
                _link(logs_dir, run["report"], "report"),
                _link(logs_dir, run["txt"], "transcript"),
                _link(logs_dir, run["pdf"], "routes.pdf"),
            ])
            hosts = run["hosts"]
            parts.append(f'<div class="run" data-search="{search}">')
            parts.append(f'<div class="stem">{html.escape(run["stem"])}</div>')
            parts.append(f'<div class="links">{links}</div>')
            if hosts:
                parts.append(f'<details><summary>{len(hosts)} host(s)</summary>'
                             '<table class="hosts">')
                for host, files in hosts.items():
                    parts.append(
                        f'<tr><td>{html.escape(host)}</td>'
                        f'<td>{_link(logs_dir, files["log"], "log")}</td>'
                        f'<td>{_link(logs_dir, files["report"], "report")}</td></tr>')
                parts.append("</table></details>")
            parts.append("</div>")
        parts.append("</section>")

    parts.append(_PAGE_TAIL)
    return "".join(parts).encode("utf-8")


def load_md_renderer() -> str | None:
    """Extract the mdToHtml() JS function from the timeline template.

    The renderer is defined once in assets/timeline_template.html (used for the
    timelines); reusing it here keeps the two markdown views identical. Returns
    None if the template can't be found, in which case .md files fall back to
    being served as plain text.
    """
    tpl = REPO_ROOT / "assets" / "timeline_template.html"
    try:
        s = tpl.read_text(encoding="utf-8")
        a = s.index("function mdToHtml(src)")
        b = s.index("// Reasoning is rendered", a)
        return s[a:b].rstrip()
    except (OSError, ValueError):
        return None


class LogsHandler(SimpleHTTPRequestHandler):
    """Static file server for the logs dir, with a generated dashboard at /."""

    logs_dir: Path  # set in main() before serving
    md_js: str | None = None  # mdToHtml() source, or None to serve .md raw

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        if route in ("/", "/index.html"):
            self._send_html(render_dashboard(self.logs_dir))
            return
        if (route.endswith(".md") and self.md_js
                and "raw" not in parse_qs(parsed.query)):
            self._serve_markdown(route)
            return
        super().do_GET()

    def _serve_markdown(self, route: str) -> None:
        fs_path = Path(self.translate_path(route))
        if not fs_path.is_file():
            self.send_error(404, "File not found")
            return
        text = fs_path.read_text(encoding="utf-8", errors="replace")
        # Escape "</" so a literal "</script>" in the markdown can't end the tag.
        src_json = json.dumps(text).replace("</", "<\\/")
        page = (_MD_PAGE
                .replace("__TITLE__", html.escape(fs_path.name))
                .replace("__RAW__", html.escape(route + "?raw=1"))
                .replace("__MD_JS__", self.md_js)
                .replace("__SRC__", src_json))
        self._send_html(page.encode("utf-8"))

    def _send_html(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def guess_type(self, path):
        ctype = super().guess_type(path)
        if Path(path).suffix.lower() in INLINE_TEXT_SUFFIXES:
            return "text/plain; charset=utf-8"
        return ctype

    def log_message(self, fmt, *args):  # quieter, single-line logging
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


_PAGE_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Experiment logs</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font: 15px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 60rem;
         padding: 1.5rem; background: #fff; color: #1c2330; }}
  h1 {{ margin: 0 0 .25rem; }}
  .sub {{ color: #888; margin: 0 0 1rem; }}
  #filter {{ width: 100%; box-sizing: border-box; padding: .5rem .6rem;
            font-size: 1rem; margin-bottom: 1.25rem; border: 1px solid #8884;
            border-radius: .4rem; }}
  section {{ margin-bottom: 1.5rem; }}
  h2 {{ font-size: 1.1rem; border-bottom: 1px solid #8883; padding-bottom: .2rem; }}
  .count {{ color: #888; font-weight: normal; font-size: .85rem; }}
  .run {{ padding: .5rem .7rem; margin: .4rem 0; border: 1px solid #8883;
         border-radius: .4rem; }}
  .stem {{ font-family: ui-monospace, monospace; font-size: .9rem;
          font-weight: 600; word-break: break-all; }}
  .links {{ margin-top: .25rem; }}
  .links a {{ text-decoration: none; }}
  .links a:hover {{ text-decoration: underline; }}
  .missing {{ color: #aaa; }}
  details {{ margin-top: .4rem; }}
  summary {{ cursor: pointer; color: #888; font-size: .85rem; }}
  table.hosts {{ margin: .4rem 0 .2rem; border-collapse: collapse; font-size: .9rem; }}
  table.hosts td {{ padding: .1rem .8rem .1rem 0; }}
  table.hosts td:first-child {{ font-family: ui-monospace, monospace; }}
</style></head><body>
<h1>Experiment logs</h1>
<p class="sub">{n_runs} run(s) across {n_cats} categor(ies) &mdash; serving <code>{root}</code></p>
<input id="filter" type="search" placeholder="Filter runs (name, category, host)&hellip;" autofocus>
"""

_PAGE_TAIL = """
<script>
  const box = document.getElementById('filter');
  box.addEventListener('input', () => {
    const q = box.value.trim().toLowerCase();
    for (const run of document.querySelectorAll('.run')) {
      run.style.display = run.dataset.search.includes(q) ? '' : 'none';
    }
    for (const sec of document.querySelectorAll('section')) {
      const any = [...sec.querySelectorAll('.run')].some(r => r.style.display !== 'none');
      sec.style.display = any ? '' : 'none';
    }
  });
</script>
</body></html>
"""

# Standalone page for a single .md file: renders it client-side with the same
# mdToHtml() used by the timelines. Placeholders: __TITLE__, __RAW__, __MD_JS__,
# __SRC__ (a JSON string literal).
_MD_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light; }
  body { font: 15px/1.6 system-ui, sans-serif; margin: 0 auto; max-width: 50rem;
         padding: 1.5rem; background: #fff; color: #1c2330; }
  .bar { display: flex; gap: 1rem; align-items: baseline; margin-bottom: 1rem;
         padding-bottom: .5rem; border-bottom: 1px solid #8883; }
  .bar .name { font-family: ui-monospace, monospace; font-weight: 600; }
  .bar a { color: #2563eb; text-decoration: none; font-size: .9rem; }
  .md > :first-child { margin-top: 0; }
  .md h1, .md h2, .md h3 { line-height: 1.25; margin: 1.4em 0 .5em; }
  .md h1 { font-size: 1.6em; } .md h2 { font-size: 1.35em; } .md h3 { font-size: 1.15em; }
  .md code { font-family: ui-monospace, Menlo, Consolas, monospace; background: #eef1f5;
             padding: 1px 5px; border-radius: 4px; font-size: .9em; }
  .md pre { background: #eef1f5; padding: 12px 14px; border-radius: 8px; overflow: auto; }
  .md pre code { background: none; padding: 0; }
  .md blockquote { margin: 1em 0; padding: .2em 0 .2em 1em; border-left: 3px solid #d6dbe3;
                   color: #667085; }
  .md a { color: #2563eb; }
  .md hr { border: none; border-top: 1px solid #d6dbe3; margin: 1.5em 0; }
  .md table { border-collapse: collapse; }
  .md th, .md td { border: 1px solid #d6dbe3; padding: 4px 9px; }
</style></head><body>
<div class="bar"><span class="name">__TITLE__</span>
  <a href="/">&larr; index</a><a href="__RAW__">raw</a></div>
<div id="md" class="md"></div>
<script>
__MD_JS__
document.getElementById("md").innerHTML = mdToHtml(__SRC__);
document.title = "__TITLE__";
</script>
</body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--logs-dir", type=Path, default=REPO_ROOT / "logs",
                        help="Logs directory to serve (default: <repo>/logs).")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Address to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to listen on (default: 8000).")
    args = parser.parse_args()

    logs_dir = args.logs_dir.resolve()
    if not logs_dir.is_dir():
        print(f"ERROR: logs directory not found: {logs_dir}", file=sys.stderr)
        return 1

    LogsHandler.logs_dir = logs_dir  # read by handler instances
    LogsHandler.md_js = load_md_renderer()
    if LogsHandler.md_js is None:
        print("WARNING: timeline template not found; serving .md files as raw text.",
              file=sys.stderr)
    handler = partial(LogsHandler, directory=str(logs_dir))

    with ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        print(f"Serving {logs_dir} at http://{args.host}:{args.port}/ "
              f"(Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
