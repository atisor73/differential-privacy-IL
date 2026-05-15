#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/rf50/opt/anaconda3/bin/python}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$ROOT/data/processed_data/DP_noise_sparse_constrained}"

cd "$ROOT"

"$PYTHON_BIN" dp_noise_pipeline_constrained.py \
  --epsilons 0.01 0.05 0.1 0.2 0.5 1 2 5 10 15 17 18 19 20 21 23 25 \
  --output-root "$OUTPUT_ROOT"
