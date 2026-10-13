#!/usr/bin/env bash
# Run one command while holding a machine-wide GPU lock, so overnight jobs never overlap.
exec flock "${GPU_LOCK:-/tmp/gpu.lock}" "$@"
