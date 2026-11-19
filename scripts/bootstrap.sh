#!/usr/bin/env bash
set -euo pipefail
umask 077
PACKAGE="$(cd "$(dirname "$0")/.." && pwd)"
export REPRO_ROOT="${REPRO_ROOT:-$PACKAGE/workspace}"
command -v python3.12 >/dev/null
command -v git >/dev/null
command -v npm >/dev/null
command -v java >/dev/null
# Node >=22 and Java 21 must be installed by the operator.
node -e 'if (+process.versions.node.split(".")[0]<22) process.exit(1)'
mkdir -p "$REPRO_ROOT/sources" "$REPRO_ROOT/runtime"
test ! -e "$REPRO_ROOT/sources/EvoAgentBench" || { echo 'Use a fresh REPRO_ROOT'; exit 1; }
git clone https://github.com/EverMind-AI/EvoAgentBench.git "$REPRO_ROOT/sources/EvoAgentBench"
git -C "$REPRO_ROOT/sources/EvoAgentBench" checkout --detach 6aa49908adef7d430b3a172d6d7c06d5224ef6d2
git clone https://github.com/EverMind-AI/EverOS.git "$REPRO_ROOT/runtime/EverOS-v1.2.3"
git -C "$REPRO_ROOT/runtime/EverOS-v1.2.3" checkout --detach 48fc9084888bc17100053227284f939a5aca5e91
ln -s "$REPRO_ROOT/sources/EvoAgentBench/benchmark" "$REPRO_ROOT/runtime/EvoAgentBench-benchmark-6aa4990"
BENCH="$REPRO_ROOT/runtime/EvoAgentBench-benchmark-6aa4990"
python3.12 -m venv "$BENCH/.benchmark-venv"
"$BENCH/.benchmark-venv/bin/pip" install -c "$PACKAGE/evidence/benchmark-constraints.txt" -r "$BENCH/requirements-ir.txt"
"$BENCH/.benchmark-venv/bin/pip" install -c "$PACKAGE/evidence/benchmark-constraints.txt" fastapi==0.162.2 uvicorn==0.54.0
python3.12 -m venv "$REPRO_ROOT/runtime/EverOS-v1.2.3/.venv"
"$REPRO_ROOT/runtime/EverOS-v1.2.3/.venv/bin/pip" install -c "$PACKAGE/evidence/everos-constraints.txt" "$REPRO_ROOT/runtime/EverOS-v1.2.3"
npm install --prefix "$REPRO_ROOT/runtime/openclaw-runtime" openclaw@2026.3.24
cp "$PACKAGE/scripts/start_official_local_search.py" "$REPRO_ROOT/runtime/"
cp "$PACKAGE/scripts/everos_local_models.py" "$REPRO_ROOT/runtime/"
printf '\nInstall complete. Configure %s/.env, then download assets.\n' "$REPRO_ROOT"
