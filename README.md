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

## Arguments

| Argument | Short | Default | Description |
|---|---|---|---|
| `--topology` | | *(required)* | Path to topology CSV file |
| `--prompt` | `-p` | *(required)* | Path to prompt file sent to each agent |
| `--model` | `-m` | `sonnet` | Model key to use for agents |
| `--log-dir` | `-d` | `logs/` | Directory for per-node log files |
| `--max-iterations` | `-i` | `30` | Max agent iterations per node |
| `--max-tokens` | `-t` | `4096` | Max tokens per LLM response |
| `--openai-host` | | `localhost` | Hostname for OpenAI-compatible API server |
| `--openai-port` | | `8000` | Port for OpenAI-compatible API server |
| `--log-level` | `-l` | `INFO` | Logging verbosity |

Per-node logs are written to `logs/<prompt>-<model>-<topology>-<node>.log` after each run.

## Open questions

- Should we give complete autonomy to the agents within their hosts? Or make them run a specific set of commands only? Right now, the latter is implemented.