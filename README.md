# Instantiating the Knowledge Plane

Research code for *Instantiating the Knowledge Plane* (HotNets 2026). LLM agents run as
autonomous system administrators on an emulated interdomain network, one agent per network
entity, and collaborate across organizational boundaries to diagnose faults, reason about
misleading routing announcements, and make policy-driven routing decisions.

Agents communicate over a **knowledge plane** — a message channel separate from the data
network — and act on their hosts by running ordinary commands. Each agent is given only its
own organization's objectives and policies: it has no global view and must discover the rest
of the network by investigating it and asking other agents.

This repository contains the emulation harness, the agent prompts, the topologies, and the
complete logs of every experiment reported in the paper.

## Repository layout

| Path | Contents |
|---|---|
| `run_experiments.py` | Runner: executes experiments declared in a TOML file, via Docker |
| `experiments.toml` | Every experiment in this repository |
| `paper_experiments.toml` | The subset reported in the paper |
| `experiments/` | Experiment entry points, one module per scenario |
| `agentic_networks/` | The library: agents, message bus, Mininet network, billing, reporting |
| `prompts/` | Per-experiment, per-node agent prompts |
| `topologies/` | Network topologies as CSV, plus rendered PDFs |
| `policies/` | Routing contracts and policies handed to agents |
| `assets/` | Emulated ACM web server and load client (TLS material is generated per run) |
| `logs/` | Full logs, transcripts, reports, and HTML timelines for every run |
| `website/` | Project landing page, published with GitHub Pages |
| `tools/` | Setup, plotting, log browsing, and analysis utilities |

## Setup

Experiments build a Mininet topology and need root and network-namespace support, so they
run inside a privileged Docker container. This is the supported path.

```bash
# Requires Docker on Linux with privileged container support.
export ANTHROPIC_API_KEY=sk-...        # forwarded into the container automatically
export OPENAI_API_KEY=...              # only for gpt-* models
export TOGETHER_API_KEY=...            # only for glm-* models
```

The image is rebuilt automatically on each run; no manual build step is needed.

<details>
<summary>Running without Docker</summary>

Requires Linux with root access. Mininet manipulates host networking, and `kp_why_fix.py`
additionally rewrites `/etc/resolv.conf` and installs a CA into the system trust store — so
running outside a container affects the whole machine for the duration of the run.
`kp_why_fix.py` refuses to start unless it detects a container; the other experiments do
not, so run them outside Docker only if you accept that they reconfigure host networking.

```bash
./tools/setup.sh                       # system packages, venv, editable install
source env/bin/activate
```

`tools/setup.sh` ends with `pip install -e .`, which puts the repository on the Python
import path. That is what lets `experiments/*.py` import `agentic_networks` when launched
by path from any directory.

</details>

## Running experiments

List what is available and run one by name:

```bash
python3 run_experiments.py --list -m opus-4-7
python3 run_experiments.py -m opus-4-7 --filter celer_bridge
```

Reproduce the experiments reported in the paper:

```bash
python3 run_experiments.py --experiments-file paper_experiments.toml -m opus-4-7
```

Runs whose final report already exists are skipped; pass `--force` to re-run them. Use
`--print-commands` to see the exact invocations without executing anything.

| Argument | Short | Description |
|---|---|---|
| `--model` | `-m` | *(required)* Model key used for every agent |
| `--experiments-file` | | TOML to read (default: `experiments.toml`) |
| `--filter` | `-f` | Run only the named experiments |
| `--list` | `-l` | List experiment names and exit |
| `--force` | `-F` | Re-run even if a final report exists |
| `--print-commands` | `-p` | Print commands and exit |
| `--debug` | | Pass `--log-level DEBUG` to each experiment |
| `--vllm-host` / `--vllm-port` | | Override the vLLM server location |

An experiment can also be launched directly, which is what the runner does:

```bash
./tools/run_in_docker.sh experiments/kp_why_fix.py --fault dns_stale --model opus-4-7
```

Every experiment script accepts `--help`.

## Models

Pass a model key with `--model`. Closed models are reached through their provider's API;
open-weight models require a running vLLM server, except GLM which is served via Together AI.

| Provider | Keys |
|---|---|
| Anthropic | `opus-4-7`, `opus-4-6`, `sonnet-4-6` |
| OpenAI | `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano` |
| Together AI | `glm-5.2` |
| vLLM (local) | `qwen2.5-72b-awq`, `qwen2.5-72b-gptq`, `qwq-32b`, `qwq-32b-awq`, `deepseek-r1-32b`, `deepseek-r1-70b-awq`, `llama3.3-70b-awq`, `mistral-small-24b`, `phi-4-14b`, `gemma-3-27b` |

To serve a local model:

```bash
./tools/spawn_vllm_openai_model.py --model qwq-32b --tensor-parallel-size 2
```

## Browsing results

Every run writes per-node logs, a transcript, a final report, and a self-contained
interactive HTML timeline into its `logs/` subdirectory. The project website indexes all
of them, and runs locally with one command:

```bash
python3 tools/serve_website.py         # http://127.0.0.1:8080
```

That builds the site into `_site/` (gitignored) and serves it: the landing page from
`website/`, a searchable dashboard of every run, and each run's timeline, report,
transcript and routes PDF. `--no-build` serves an existing build without rebuilding.

The site is published to GitHub Pages by `.github/workflows/pages.yml`, which runs the
same `tools/build_website.py`. The built site is never committed — logs are assembled
into it at deploy time rather than duplicated in the repository.

## Citation

See [`CITATION.cff`](CITATION.cff). It is a placeholder until the camera-ready version is
published, at which point the proceedings title, DOI and pages will be filled in.

## License

MIT — see [`LICENSE`](LICENSE).

The logs under `logs/` contain model output generated by third-party services (Anthropic,
OpenAI, Together AI) and are published as experimental records of the runs reported in the
paper.
