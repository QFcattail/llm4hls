#!/usr/bin/env bash
# FPGA Agent - 一行启动脚本
# 用法: ./run.sh [fpga-agent.py 的所有参数]
#
# 自动 source: Vitis settings64.sh + .env (DeepSeek API key) + Python venv
# 你只需要: ssh QFS-STATION && cd /home/admin/fpga-agent && ./run.sh

set -eo pipefail
cd "$(dirname "$0")"

# 1. Vitis 工具链（csim/synth/cosim 必需）
VITIS_SETTINGS="/home/admin/Xilinx/2025.2/Vitis/settings64.sh"
if [ -f "$VITIS_SETTINGS" ]; then
    source "$VITIS_SETTINGS"
else
    echo "WARN: Vitis settings64.sh not found at $VITIS_SETTINGS" >&2
fi

# 2. DeepSeek API key
if [ -f ".env" ]; then
    source .env
else
    echo "WARN: .env not found (DEEPSEEK_API_KEY not loaded)" >&2
fi

# 3. Python 3.12 venv
VENV="/home/admin/venv-fpga/bin/activate"
if [ -f "$VENV" ]; then
    source "$VENV"
else
    echo "WARN: venv not found at $VENV, using system python3" >&2
fi

# 4. 启动 agent
exec python3 fpga-agent.py "$@"
