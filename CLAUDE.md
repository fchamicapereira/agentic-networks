# A Futuristic Network

In this project, we will test the feasibility of having a fully autonomous network controlled by agentic models. The general idea is to have an LLM-controlled control plane. The LLMs should be able to write/manipulate routing rules, communicate with each other using whatever methods or protocol they prefer (e.g. natural language, bit signals, or even entire custom protocols designed by the agents).

This project will contain emulated network topologies while providing LLMs some rudimentary background on routing, possibly give it higher level economic constraints without explicitly defining what to do with those constraints, and test under different workloads and see what emergent behavior comes out of this.