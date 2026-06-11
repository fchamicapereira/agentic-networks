#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

cd "$SCRIPT_DIR"/..

sudo apt-get update
sudo apt-get install -y \
  git build-essential \
  mininet \
  iproute2 iputils-ping \
  python3-pip python3-setuptools python3-dev \
  python3-tk python3-numpy python3-scipy python3-matplotlib \
  python3.10-venv \
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
  strace

python3 -m venv env
pip3 install -r requirements.txt