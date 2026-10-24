#!/usr/bin/env python3
"""build_website.py — Assemble the project website as a static site.

Produces a directory that can be served as-is: the landing page from website/ at the
root, and every experiment artifact under logs/, indexed by a generated dashboard.

    <output>/index.html          the landing page (from website/)
    <output>/logs/index.html     generated dashboard of all runs
    <output>/logs/<category>/    timelines, reports, transcripts, routes PDFs
    <output>/logs/**/*.md.html   reports pre-rendered for the browser
    <output>/paper-data/         the frozen snapshot of the paper's runs, with its own index
    <output>/demo/recordings/    the paper runs as demo event streams (demo/EVENTS.md)

Both the local server (tools/serve_website.py) and the GitHub Pages workflow call this,
so what you see locally is byte-for-byte what gets deployed.

Every link generated here is relative. The deployed site is a *project* page living under
https://<user>.github.io/<repo>/, so an absolute "/logs/..." would resolve against the
domain root and 404.

Usage:
    python3 tools/build_website.py                  # build into <repo>/_site
    python3 tools/build_website.py -o /tmp/site
    python3 tools/build_website.py --clean
"""

import argparse
import html
import json
import os
import shutil
import sys

from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "demo" / "tools"))

import logs_to_events  # noqa: E402

PAPER_DATA = REPO_ROOT / "paper-data"
DEFAULT_OUTPUT = REPO_ROOT / "_site"

FINAL_SUFFIX = "-final-report.md"
HOST_REPORT_SUFFIX = "-report.md"


# --- run discovery ---------------------------------------------------------------

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
            def sibling(suffix: str, _d=d, _stem=stem) -> Path | None:
                p = _d / f"{_stem}{suffix}"
                return p if p.exists() else None

            hosts = {h: {"log": v.get("log"), "report": v.get("report")}
                     for h, v in sorted(hosts_by_stem.get(stem, {}).items())}
            runs_by_category[category].append({
                "stem": stem,
                "report": d / f"{stem}{FINAL_SUFFIX}",
                "moments": sibling("-reasoning-moments.md"),
                "html": sibling(".html"),
                "txt": sibling(".txt"),
                "pdf": sibling("-routes.pdf"),
                "hosts": hosts,
            })

    return runs_by_category


# --- dashboard -------------------------------------------------------------------

def _url(logs_dir: Path, path: Path) -> str:
    """Link target relative to the dashboard, which sits at the logs root.

    Markdown is linked through its pre-rendered sibling so the browser shows a
    formatted report rather than downloading the source.
    """
    rel = path.relative_to(logs_dir)
    if rel.suffix == ".md":
        rel = rel.with_name(rel.name + ".html")
    return quote(str(rel))


def _link(logs_dir: Path, path: Path | None, label: str) -> str:
    if path is None:
        return f'<span class="missing">{html.escape(label)}</span>'
    return f'<a href="{_url(logs_dir, path)}">{html.escape(label)}</a>'


def render_dashboard(logs_dir: Path) -> bytes:
    runs_by_category = discover_runs(logs_dir)
    total_runs = sum(len(v) for v in runs_by_category.values())

    parts: list[str] = [_PAGE_HEAD.format(
        n_runs=total_runs, n_cats=len(runs_by_category))]

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
                _link(logs_dir, run["moments"], "quotes"),
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


# --- paper data page ---------------------------------------------------------------

def render_paper_page(paper_out: Path) -> bytes:
    """Index of the frozen paper snapshot, driven by its runs.json: one table per scenario,
    one row per model, linking each run's replay, timeline, reports, and agent logs."""
    meta = json.loads((paper_out / "runs.json").read_text())

    def link(rel: str | None, label: str) -> str:
        if rel is None or not (paper_out / rel).exists():
            return f'<span class="missing">{html.escape(label)}</span>'
        if rel.endswith(".md"):
            rel += ".html"
        return f'<a href="{quote(rel)}">{html.escape(label)}</a>'

    parts = [_PAPER_HEAD.format(paper=html.escape(meta["paper"]), commit=html.escape(meta["source_commit"][:7]),
                                n=sum(len(s["runs"]) for s in meta["scenarios"]))]
    for sc in meta["scenarios"]:
        parts.append(f'<section><h2>{html.escape(sc["title"])}</h2>'
                     f'<p class="where">{html.escape(sc["paper"])}</p><table class="runs">'
                     '<tr><th>Model</th><th>Watch</th><th>Read</th><th>Raw</th></tr>')
        for run in sc["runs"]:
            stem, d = run["stem"], sc["logs_dir"]

            def f(suffix: str, _d=d, _stem=stem, _files=run["files"]) -> str | None:
                rel = f"{_d}/{_stem}{suffix}"
                return rel if rel in _files else None

            agents = " ".join(link(f"{d}/{stem}-{n}.log", n) for n in sc["nodes"])
            extras = [link(f(sfx), label) for sfx, label in
                      ((".txt", "transcript"), ("-routes.pdf", "routes.pdf"), ("-data.json", "traffic data"),
                       ("-tput-paper.pdf", "Figure 3")) if f(sfx)]
            parts.append(
                f'<tr><td class="model">{html.escape(run["model_label"])}</td>'
                f'<td><a href="../demo/#{quote(sc["id"])}/{quote(run["model"])}">replay</a> &middot; '
                f'{link(f(".html"), "timeline")}</td>'
                f'<td>{link(f("-final-report.md"), "final report")} &middot; '
                f'{link(f("-reasoning-moments.md"), "quotes")}</td>'
                f'<td><details><summary>agent logs</summary>{agents}</details>'
                + "".join(f" &middot; {e}" for e in extras) + '</td></tr>')
        parts.append("</table></section>")
    inputs = sorted(p.relative_to(paper_out).as_posix() for p in (paper_out / "inputs").rglob("*")
                    if p.is_file() and not p.name.endswith(".md.html"))
    parts.append('<section><h2>Inputs</h2><p class="where">What the agents were given: prompts, '
                 'topologies, the experiment config, and the code defining the shared system prompt, '
                 'tools, and each scenario.</p><ul class="inputs">'
                 + "".join(f"<li>{link(rel, rel[len('inputs/'):])}</li>" for rel in inputs) + "</ul></section>")
    parts.append(_PAPER_TAIL)
    return "".join(parts).encode("utf-8")


# --- markdown pre-rendering ------------------------------------------------------

def load_md_renderer() -> str | None:
    """Extract the mdToHtml() JS function from the timeline template.

    The renderer is defined once in assets/timeline_template.html (used for the
    timelines); reusing it here keeps the two markdown views identical. Returns
    None if the template can't be found, in which case .md files are left as
    plain text with no rendered sibling.
    """
    tpl = REPO_ROOT / "assets" / "timeline_template.html"
    try:
        s = tpl.read_text(encoding="utf-8")
        a = s.index("function mdToHtml(src)")
        b = s.index("// Reasoning is rendered", a)
        return s[a:b].rstrip()
    except (OSError, ValueError):
        return None


def render_markdown_pages(logs_out: Path, md_js: str) -> int:
    """Write a browsable <name>.md.html beside every .md file under logs_out."""
    index = logs_out / "index.html"
    count = 0
    for md in sorted(logs_out.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        # Escape "</" so a literal "</script>" in the markdown can't end the tag.
        src_json = json.dumps(text).replace("</", "<\\/")
        page = (_MD_PAGE
                .replace("__TITLE__", html.escape(md.name))
                .replace("__INDEX__", html.escape(os.path.relpath(index, md.parent)))
                .replace("__RAW__", html.escape(quote(md.name)))
                .replace("__MD_JS__", md_js)
                .replace("__SRC__", src_json))
        md.with_name(md.name + ".html").write_text(page, encoding="utf-8")
        count += 1
    return count


# --- assembly --------------------------------------------------------------------

def sync_tree(src: Path, dst: Path) -> int:
    """Copy src into dst, skipping files already identical in size and mtime.

    Rebuilds during local iteration then cost a directory walk rather than a fresh
    copy of every log artifact.
    """
    copied = 0
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        target = dst / path.relative_to(src)
        if target.exists():
            s, t = path.stat(), target.stat()
            if s.st_size == t.st_size and int(s.st_mtime) == int(t.st_mtime):
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def build(website_dir: Path, logs_dir: Path, output: Path, clean: bool = False,
          paper_dir: Path = PAPER_DATA) -> None:
    if clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    n_page = sync_tree(website_dir, output)
    print(f"  landing page : {n_page} file(s) from {website_dir.relative_to(REPO_ROOT)}/")

    logs_out = output / "logs"
    n_logs = sync_tree(logs_dir, logs_out)
    print(f"  log artifacts: {n_logs} file(s) copied, {sum(1 for _ in logs_out.rglob('*') if _.is_file())} total")

    (logs_out / "index.html").write_bytes(render_dashboard(logs_out))
    print("  dashboard    : logs/index.html")

    md_js = load_md_renderer()
    if md_js is None:
        print("  WARNING: timeline template not found; .md files left unrendered.", file=sys.stderr)
    else:
        n_md = render_markdown_pages(logs_out, md_js)
        print(f"  markdown     : {n_md} report(s) pre-rendered")

    paper_out = output / "paper-data"
    if paper_dir.is_dir():
        sync_tree(paper_dir, paper_out)
        (paper_out / "index.html").write_bytes(render_paper_page(paper_out))
        if md_js is not None:
            render_markdown_pages(paper_out, md_js)
        print("  paper data   : paper-data/ (frozen snapshot of the paper's runs)")
        n_rec = logs_to_events.write_recordings(output / "demo" / "recordings", paper_dir)
        print(f"  demo         : {n_rec} recording(s) in demo/recordings/")
    else:
        print(f"  WARNING: {paper_dir} not found; no paper data page and no demo recordings.", file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT,
                        help="Directory to build into (default: <repo>/_site)")
    parser.add_argument("--website-dir", type=Path, default=REPO_ROOT / "website",
                        help="Source of the landing page (default: <repo>/website)")
    parser.add_argument("--logs-dir", type=Path, default=REPO_ROOT / "logs",
                        help="Experiment logs to publish (default: <repo>/logs)")
    parser.add_argument("--clean", action="store_true",
                        help="Delete the output directory before building")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for label, d in (("website", args.website_dir), ("logs", args.logs_dir)):
        if not d.is_dir():
            print(f"ERROR: {label} directory not found: {d}", file=sys.stderr)
            return 1

    print(f"Building site into {args.output}")
    build(args.website_dir, args.logs_dir, args.output, clean=args.clean)
    print("Done.")
    return 0


# --- page templates --------------------------------------------------------------

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
  .paper-note {{ margin: 0 0 1rem; padding: .5rem .7rem; border-left: 3px solid #2563eb;
                background: #f4f7fd; }}
  .paper-note a {{ color: #2563eb; font-weight: 600; }}
  .home {{ display: inline-block; margin-bottom: 1rem; color: #2563eb;
          text-decoration: none; font-size: .9rem; }}
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
<a class="home" href="../index.html">&larr; Instantiating the Knowledge Plane</a>
<h1>Experiment logs</h1>
<p class="sub">{n_runs} run(s) across {n_cats} categor(ies)</p>
<p class="paper-note">Every run, including exploratory ones that are not in the paper.
The runs reported in the paper are in <a href="../paper-data/">Paper data</a>.</p>
<input id="filter" type="search" placeholder="Filter runs (name, category, host)&hellip;" autofocus>
"""

_PAPER_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paper data</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font: 15px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 60rem;
         padding: 1.5rem; background: #fff; color: #1c2330; }}
  h1 {{ margin: 0 0 .25rem; }}
  .sub {{ margin: 0 0 .5rem; }}
  .frozen {{ margin: 0 0 1.5rem; padding: .55rem .8rem; border-left: 3px solid #2563eb;
            background: #f4f7fd; font-size: .92rem; }}
  .home {{ display: inline-block; margin-bottom: 1rem; color: #2563eb;
          text-decoration: none; font-size: .9rem; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  section {{ margin-bottom: 1.8rem; }}
  h2 {{ font-size: 1.1rem; border-bottom: 1px solid #8883; padding-bottom: .2rem; margin-bottom: .2rem; }}
  .where {{ color: #666; margin: 0 0 .5rem; font-size: .9rem; }}
  table.runs {{ border-collapse: collapse; width: 100%; font-size: .92rem; table-layout: fixed; }}
  table.runs th:nth-child(1) {{ width: 24%; }} table.runs th:nth-child(2) {{ width: 20%; }}
  table.runs th:nth-child(3) {{ width: 24%; }}
  table.runs th {{ text-align: left; font-weight: 600; color: #666; font-size: .8rem;
                  border-bottom: 1px solid #8883; padding: .2rem .6rem .2rem 0; }}
  table.runs td {{ padding: .35rem .6rem .35rem 0; border-bottom: 1px solid #8882; vertical-align: top; }}
  td.model {{ font-weight: 600; white-space: nowrap; }}
  details {{ display: inline; }}
  summary {{ cursor: pointer; color: #2563eb; display: inline; }}
  details[open] summary {{ margin-right: .4rem; }}
  .missing {{ color: #aaa; }}
  ul.inputs {{ columns: 2; font-family: ui-monospace, monospace; font-size: .85rem; padding-left: 1.2rem; }}
  code {{ font-family: ui-monospace, monospace; }}
  @media (max-width: 640px) {{ ul.inputs {{ columns: 1; }} table.runs {{ font-size: .85rem; }} }}
</style></head><body>
<a class="home" href="../index.html">&larr; Instantiating the Knowledge Plane</a>
<h1>Paper data</h1>
<p class="sub">The {n} runs reported in <em>{paper}</em>.</p>
<p class="frozen"><strong>Frozen snapshot.</strong> These files are exactly the runs the paper
reports, copied from commit <code>{commit}</code> and never changed since: every file is listed
with its SHA-256 in <a href="MANIFEST.sha256">MANIFEST.sha256</a>
(<a href="README.md.html">about this snapshot</a>, <a href="runs.json">runs.json</a>).
Later and exploratory runs are in the <a href="../logs/">full experiment log</a>.</p>
"""

_PAPER_TAIL = """
</body></html>
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
# mdToHtml() used by the timelines. Placeholders: __TITLE__, __INDEX__, __RAW__,
# __MD_JS__, __SRC__ (a JSON string literal).
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
  <a href="__INDEX__">&larr; index</a><a href="__RAW__">raw</a></div>
<div id="md" class="md"></div>
<script>
__MD_JS__
document.getElementById("md").innerHTML = mdToHtml(__SRC__);
document.title = "__TITLE__";
</script>
</body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
