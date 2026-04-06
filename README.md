# Talkative Control Protocol

An experiment in autonomous, LLM-driven network control planes. Independent Claude agents run on each node of an emulated network and must figure out how to route traffic — with no shared state, no pre-configured routes, and no human guidance beyond their initial prompt.

## How it works

A full-mesh Mininet topology is created with 4 nodes (`h1`–`h4`). Each pair of nodes is connected by a direct link with a specific latency. All routing tables start empty. One Claude agent is spawned per node in a separate thread; the agents run in parallel and share no context with each other.

Each agent can inspect its own interfaces, add and delete routes, and ping peers. The goal is for every node to reach every other node. After all agents call `report_done`, a connectivity matrix is printed showing the result.

```
Topology (full mesh):

  h1 10.0.12.1/30  <──[10ms]──>  h2 10.0.12.2/30
  h1 10.0.13.1/30  <──[20ms]──>  h3 10.0.13.2/30
  h1 10.0.14.1/30  <──[ 5ms]──>  h4 10.0.14.2/30
  h2 10.0.23.1/30  <──[15ms]──>  h3 10.0.23.2/30
  h2 10.0.24.1/30  <──[30ms]──>  h4 10.0.24.2/30
  h3 10.0.34.1/30  <──[25ms]──>  h4 10.0.34.2/30
```

## Setup

### With Docker

Requires Docker and Linux with privileged container support.

```bash
# Build the image and run the script (image is rebuilt automatically on each run)
./tools/run_in_docker.sh simple_routing.py \
    --topology topologies/pair.csv \
    --prompt prompts/routing_simple.txt \
    --model qwen2.5-72b
```

Pass any `simple_routing.py` arguments after the script name. The script runs inside the container with the project directory mounted at `/workspace`.

For Claude models, set `ANTHROPIC_API_KEY` in your environment before running — it is forwarded automatically into the container.

### Without Docker

Requires Linux with root access (Mininet runs in network namespaces).

```bash
# Install system dependencies and create the virtualenv
./setup.sh

# Activate the virtualenv
source env/bin/activate

export ANTHROPIC_API_KEY=sk-...
```

Mininet requires root. Use `sudo -E` to preserve environment variables:

```bash
sudo -E env/bin/python3 simple_routing.py \
    --topology topologies/pair.csv \
    --prompt prompts/routing_simple.txt \
    --model qwen2.5-72b
```

Run with `-h` to see the full help menu:

```bash
sudo -E env/bin/python3 simple_routing.py -h
```

## Models

Pass a model key via `--model`. Claude models are served via the Anthropic API; local models require a running vLLM server (see `tools/spawn_vllm_openai_model.py`).

> **Size notation:** *B* = billion parameters (larger = more capable but slower/heavier). *FP16* = full 16-bit precision. *AWQ* and *GPTQ* are 4-bit quantization schemes that cut VRAM roughly in half at some quality cost.

### Claude (Anthropic API)

| Key | Description |
|-----|-------------|
| `sonnet` | Claude Sonnet 4.6 — Anthropic's balanced model |
| `opus` | Claude Opus 4.6 — Anthropic's most capable model |

### Local (vLLM / OpenAI-compatible)

| Key | Description | VRAM |
|-----|-------------|------|
| `qwen2.5-72b-awq` | Qwen 2.5 72B, AWQ 4-bit quantized | ~36 GB |
| `qwen2.5-72b-gptq` | Qwen 2.5 72B, GPTQ Int4 quantized | ~36 GB |
| `qwq-32b` | QwQ 32B — Qwen's reasoning model (chain-of-thought), FP16 | ~64 GB |
| `qwq-32b-awq` | QwQ 32B reasoning model, AWQ 4-bit quantized | ~18 GB |
| `deepseek-r1-32b` | DeepSeek-R1 reasoning model distilled into a 32B Qwen base, FP16 | ~64 GB |
| `deepseek-r1-70b-awq` | DeepSeek-R1 reasoning model distilled into a 70B Llama base, FP16 | ~140 GB |
| `llama3.3-70b-awq` | Llama 3.3 70B by Meta, AWQ 4-bit quantized | ~35 GB |
| `mistral-small-24b` | Mistral Small 3.1 24B (Apache 2.0), FP16 | ~48 GB |
| `phi-4-14b` | Phi-4 14B by Microsoft (MIT license), FP16 | ~28 GB |
| `gemma-3-27b` | Gemma 3 27B by Google, FP16 | ~54 GB |

To start a vLLM server for a local model:

```bash
./tools/spawn_vllm_openai_model.py --model qwq-32b --tensor-parallel-size 2
```

## Arguments

| Argument | Short | Default | Description |
|---|---|---|---|
| `--topology` | | *(required)* | Path to topology CSV file |
| `--prompt` | `-p` | *(required)* | Path to prompt file sent to each agent |
| `--model` | `-m` | `sonnet` | Model key to use for agents |
| `--log-dir` | `-d` | `logs/` | Directory for per-node log files |
| `--max-iterations` | `-i` | `50` | Max agent iterations per node |
| `--max-tokens` | `-t` | `16384` | Max tokens per LLM response |
| `--openai-host` | | `localhost` | Hostname for OpenAI-compatible API server |
| `--openai-port` | | `8000` | Port for OpenAI-compatible API server |
| `--log-level` | `-l` | `INFO` | Logging verbosity |

Per-node logs are written to `logs/<prompt>-<model>-<topology>-<node>.log` after each run.

## Open questions

- Should we give complete autonomy to the agents within their hosts? Or make them run a specific set of commands only? Right now, the latter is implemented.