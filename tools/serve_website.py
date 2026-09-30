#!/usr/bin/env python3
"""serve_website.py — Build the project website and serve it locally.

Runs tools/build_website.py, then serves the result as static files. The GitHub Pages
workflow runs the same build and publishes its output, so what you see here is what
gets deployed — including the full experiment log browser under /logs/.

Usage:
    python3 tools/serve_website.py                 # build, then http://127.0.0.1:8080
    python3 tools/serve_website.py --port 9000
    python3 tools/serve_website.py --no-build      # serve the existing build as-is
    python3 tools/serve_website.py --no-open       # do not launch a browser
"""

import argparse
import sys
import webbrowser

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling tools

import build_website

REPO_ROOT = Path(__file__).resolve().parent.parent

# Served inline as UTF-8 text so they render in the browser instead of downloading.
INLINE_TEXT_SUFFIXES = {".md", ".log", ".txt", ".json", ".csv"}


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # The point of this server is to see edits immediately; a cached page
        # makes it look like a rebuild did not take.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path):
        if Path(path).suffix.lower() in INLINE_TEXT_SUFFIXES:
            return "text/plain; charset=utf-8"
        return super().guess_type(path)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {self.address_string()} - {fmt % args}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Address to bind (default: 127.0.0.1)")
    parser.add_argument("--output", "-o", type=Path, default=build_website.DEFAULT_OUTPUT,
                        help="Build directory to serve (default: <repo>/_site)")
    parser.add_argument("--no-build", action="store_true", help="Serve the existing build without rebuilding")
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser window")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.no_build:
        print(f"Building site into {args.output}")
        build_website.build(
            website_dir=REPO_ROOT / "website",
            logs_dir=REPO_ROOT / "logs",
            output=args.output,
        )

    if not (args.output / "index.html").is_file():
        print(f"ERROR: no index.html under {args.output} — run without --no-build.", file=sys.stderr)
        return 1

    handler = partial(Handler, directory=str(args.output))
    with ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        url = f"http://{args.host}:{args.port}/"
        print(f"Serving {args.output} at {url}  (Ctrl-C to stop)")
        if not args.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
