#!/usr/bin/env bash
# docker-run.sh - run the FPGA Agent inside the Docker image with host Vitis.
#
# This mirrors the official contest/fpt26-harness/run-vitis.sh model: the
# Vitis 2025.2 install (too large / license-bound to bake into the image) is
# bind-mounted read-only from the host, and the harness locates it via
# LLM4HLS_VITIS_HLS_ROOT (set in the Dockerfile to /opt/xilinx/2025.2/Vitis).
#
# Usage:
#   ./docker-run.sh <task_dir> [run_agent.py args...]
#   ./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix
#   ./docker-run.sh contest/fpt26-harness/tasks/projection_bugfix --backend deepseek
#   ./docker-run.sh --tui contest/fpt26-harness/tasks/projection_bugfix   # interactive TUI
#
# Required host env / paths (override via env vars below):
#   VITIS_ROOT   host path to Vitis 2025.2 install containing settings64.sh
#   DEEPSEEK_API_KEY  (or a .env file in repo root) for --backend deepseek
#
set -eo pipefail
cd "$(dirname "$0")"

IMAGE="${IMAGE:-fpga-agent:latest}"
# Host Vitis root: default to the QFS-STATION install path. Override with
# VITIS_ROOT env var if your Vitis lives elsewhere. The Vitis settings64.sh
# sources sibling dirs (DocNav, Vivado, Model_Composer) via HARDCODED absolute
# paths under the Xilinx parent, so we must mount the whole Xilinx tree at the
# same host path inside the container (not a custom /opt/xilinx path).
VITIS_ROOT="${VITIS_ROOT:-/home/admin/Xilinx/2025.2/Vitis}"
# XILINX_PARENT = the directory containing DocNav/2025.2/etc (one level above
# the version dir, two levels above Vitis/).
XILINX_PARENT="$(dirname "$(dirname "$VITIS_ROOT")")"   # /home/admin/Xilinx
REPO_ROOT="$(pwd)"

# ---- parse --tui flag ------------------------------------------------------
TUI_MODE=0
ARGS=()
for arg in "$@"; do
    if [ "$arg" = "--tui" ]; then
        TUI_MODE=1
    else
        ARGS+=("$arg")
    fi
done
if [ ${#ARGS[@]} -eq 0 ]; then
    echo "Usage: $0 <task_dir> [run_agent.py args...]" >&2
    echo "       $0 --tui <task_dir>   (interactive TUI dashboard)" >&2
    exit 1
fi

# ---- sanity checks ---------------------------------------------------------
if [ ! -d "$VITIS_ROOT" ]; then
    echo "ERROR: Vitis 2025.2 not found at: $VITIS_ROOT" >&2
    echo "" >&2
    echo "  The agent needs Vitis HLS for csim/synth/cosim. It is NOT baked into" >&2
    echo "  the Docker image (~92 GB, license-bound) -- it is mounted from the host." >&2
    echo "" >&2
    echo "  Fix: set VITIS_ROOT to the directory containing settings64.sh:" >&2
    echo "    VITIS_ROOT=/opt/Xilinx/2025.2/Vitis $0 $*" >&2
    echo "" >&2
    echo "  If you don't have Vitis installed, download it from:" >&2
    echo "    https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vitis.html" >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon not available." >&2
    echo "" >&2
    echo "  Make sure Docker is installed and running:" >&2
    echo "    sudo systemctl start docker" >&2
    echo "    sudo usermod -aG docker \$USER   # then log out and back in" >&2
    exit 1
fi
# Check image exists
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "ERROR: Docker image '$IMAGE' not found." >&2
    echo "" >&2
    echo "  Build it first:" >&2
    echo "    docker build -t $IMAGE ." >&2
    echo "" >&2
    echo "  If docker build fails due to network issues (Docker Hub unreachable):" >&2
    echo "    - Try a registry mirror: https://docs.docker.com/docker-hub/mirror/" >&2
    echo "    - Or set a proxy: docker build --build-arg http_proxy=... -t $IMAGE ." >&2
    exit 1
fi

# Mounts:
#   1. Host Xilinx tree -> same path in container (read-only). Vitis
#      settings64.sh hardcodes absolute paths to sibling dirs (DocNav,
#      Vivado, Model_Composer), so the whole tree must be mounted at the
#      identical host path, not a remapped /opt/xilinx path.
#   2. runs/ -> /opt/fpga-agent/runs (persist outputs to host)
# API key is passed via -e env, not baked in.
RUN_ARGS=(--rm -v "${XILINX_PARENT}:${XILINX_PARENT}:ro")
# Tell harness where settings64.sh lives (must match the host path since
# settings64.sh uses hardcoded absolute paths to siblings).
RUN_ARGS+=(-e "LLM4HLS_VITIS_HLS_ROOT=${VITIS_ROOT}")

# API key: pass via env so .env never needs to be in the image.
# Also pass all LLM_* env vars for model endpoint/ID/thinking overrides.
if [ -n "$DEEPSEEK_API_KEY" ]; then
    RUN_ARGS+=("-e" "DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY")
fi
# Pass all LLM_* env vars (endpoint, model, thinking, timeout, etc.)
for var in LLM_API_KEY LLM_BASE_URL LLM_MODEL LLM_THINKING LLM_TEMPERATURE LLM_TIMEOUT LLM_MAX_RETRIES LLM_RETRY_BASE_DELAY; do
    if [ -n "${!var}" ]; then
        RUN_ARGS+=("-e" "$var=${!var}")
    fi
done
# If no keys in shell env, try .env file
if [ -z "$DEEPSEEK_API_KEY" ] && [ -z "$LLM_API_KEY" ] && [ -f "$REPO_ROOT/.env" ]; then
    # Source .env to extract all vars, then pass them through.
    # shellcheck disable=SC1090
    set -a; source "$REPO_ROOT/.env"; set +a
    [ -n "$DEEPSEEK_API_KEY" ] && RUN_ARGS+=("-e" "DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY")
    for var in LLM_API_KEY LLM_BASE_URL LLM_MODEL LLM_THINKING LLM_TEMPERATURE LLM_TIMEOUT LLM_MAX_RETRIES LLM_RETRY_BASE_DELAY; do
        if [ -n "${!var}" ]; then
            RUN_ARGS+=("-e" "$var=${!var}")
        fi
    done
fi

# Persist run outputs to the host so they survive container removal.
mkdir -p "$REPO_ROOT/runs"
RUN_ARGS+=("-v" "$REPO_ROOT/runs:/opt/fpga-agent/runs")

# TUI needs a TTY; CLI mode does not.
if [ "$TUI_MODE" -eq 1 ]; then
    RUN_ARGS+=("-it" "--entrypoint" "python3" "fpga-agent.py" "--task")
else
    RUN_ARGS+=("-i")
fi

RUN_ARGS+=("$IMAGE" "${ARGS[@]}")

echo ">> Running fpga-agent in Docker (image=$IMAGE, vitis=$VITIS_ROOT)"
exec docker run "${RUN_ARGS[@]}"
