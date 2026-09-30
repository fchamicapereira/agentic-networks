FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y \
  sudo \
  git build-essential \
  mininet \
  frr \
  iproute2 iputils-ping \
  python3-pip python3-setuptools python3-dev \
  python3-tk python3-numpy python3-scipy python3-matplotlib \
  python3.10-venv \
  graphviz \
  iperf3 \
  curl \
  openssl \
  dnsmasq \
  dnsutils \
  iptables \
  wget \
  traceroute \
  tcpdump \
  nmap \
  mtr \
  netcat-openbsd \
  net-tools \
  iputils-arping \
  iputils-tracepath \
  socat \
  lsof \
  strace \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python3 -m venv env \
  && env/bin/pip3 install --no-cache-dir -r requirements.txt

ENV PATH="/app/env/bin:$PATH"

ARG UID
ARG GID

RUN test -n "${UID}" || { echo "ERROR: --build-arg UID is required"; exit 1; } && \
  test -n "${GID}" || { echo "ERROR: --build-arg GID is required"; exit 1; }

RUN groupadd -o -g "${GID}" appgroup && \
  useradd -u "${UID}" -g "${GID}" -m appuser && \
  echo "appuser ALL=(ALL) NOPASSWD:SETENV:ALL" >> /etc/sudoers && \
  chown -R "${UID}:${GID}" /app

COPY . .

# Experiments live in experiments/ and are launched by path, so Python puts that
# subdirectory — not the repository root — on sys.path and `import agentic_networks`
# would fail. tools/run_in_docker.sh bind-mounts the working checkout over /workspace and
# runs from there, so the root to import from is /workspace, NOT the /app copy baked in
# above. Deliberately not `pip install -e /app`: that would shadow the mounted checkout
# with this stale copy, and paths.py would then resolve topologies/, prompts/ and logs/
# inside the image, so results would be written where the caller never sees them.
#
# A .pth file rather than ENV PYTHONPATH: the runner invokes the interpreter through
# `sudo -E` (Mininet needs root), and sudo strips PYTHONPATH from the environment even
# with -E, because it is one of the variables it refuses to inherit. A .pth in the venv's
# site-packages belongs to the interpreter itself, so it survives the privilege change.
RUN env/bin/python3 -c "\
import pathlib, sysconfig; \
pathlib.Path(sysconfig.get_paths()['purelib'], 'workspace.pth').write_text('/workspace\n')"

# Experiments run as root (Mininet) against the bind-mounted checkout, so any .pyc CPython
# writes lands in the user's working tree owned by root — __pycache__ directories they then
# cannot delete without sudo. Nothing here benefits from caching bytecode across runs.
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser
