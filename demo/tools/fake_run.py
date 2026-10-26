#!/usr/bin/env python3
"""fake_run.py — Play a recording back as if it were a live run, for testing the demo server.

Writes the recording's events to an events file at the pace they happened (or `--speed` times
faster), one line at a time, as an experiment run with --events does. demo/server.py --fake
starts this instead of a real experiment, so the server and the live viewer can be tested
without Docker or models. Stops like a real run: on SIGINT it ends the stream with
run_end "stopped".

    python3 demo/tools/fake_run.py RECORDING.jsonl EVENTS.jsonl [--speed 10]
"""

import argparse
import json
import sys
import time

from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("recording", type=Path)
    parser.add_argument("events", type=Path)
    parser.add_argument("--speed", type=float, default=1.0, help="how many times faster than the run (default: 1)")
    args = parser.parse_args()

    events = [json.loads(line) for line in args.recording.read_text().splitlines() if line.strip()]
    events[0]["source"] = "live"
    start = time.monotonic()
    with open(args.events, "w", encoding="utf-8") as out:
        def write(event: dict) -> None:
            out.write(json.dumps(event, ensure_ascii=False) + "\n")
            out.flush()

        try:
            for event in events:
                time.sleep(max(0.0, start + event["t"] / args.speed - time.monotonic()))
                write(event)
        except KeyboardInterrupt:
            write({"t": round((time.monotonic() - start) * args.speed, 3), "type": "run_end", "reason": "stopped"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
