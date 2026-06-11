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

USER appuser
