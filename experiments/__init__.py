"""Experiment entry points.

Each module here is a runnable experiment; see ``experiments.toml`` for the registered
runs and ``run_experiments.py`` for the runner. This is a package so that experiments
can import one another (e.g. the converged-routing and oracle variants reuse the base
experiment's ``run``) regardless of the working directory they are launched from.
"""
