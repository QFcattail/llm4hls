#!/usr/bin/env bash
# run_matrix.sh - 在 QFS-STATION 上跑 一个模型 × 任务矩阵
# 用法: ./run_matrix.sh <model> <task_dir...>
# 每个任务产物在 runs/<model>/<task_name>/（transcript.txt + jsonl + grade/）
set -o pipefail   # 不能用 set -u：Vitis settings64.sh 引用未定义变量
cd /home/admin/fpga-agent

MODEL="$1"; shift
TASKS=("$@")

# 1. Vitis 工具链
source /home/admin/Xilinx/2025.2/Vitis/settings64.sh
export LLM4HLS_VITIS_HLS_ROOT="/home/admin/Xilinx/2025.2/Vitis"
# 2. 密钥（.env.qwen 在 .env 之后 source，LLM_* 覆盖 DeepSeek 默认值）
source .env
source .env.qwen
# 3. Python venv
source /home/admin/venv-fpga/bin/activate

export LLM_MODEL="$MODEL"

for T in "${TASKS[@]}"; do
  NAME=$(basename "$T")
  # --work 必须绝对路径：harness 会 cd 进 build 目录，相对路径会被拼错
  WORK="$PWD/runs/${MODEL}/${NAME}"
  mkdir -p "$WORK"
  echo "=== [$(date -Is)] START $MODEL / $NAME ==="
  python3 scripts/run_agent.py "$T" --backend deepseek \
      --token-mode full --work "$WORK" > "$WORK/transcript.txt" 2>&1
  echo "=== [$(date -Is)] EXIT=$? $MODEL / $NAME ==="
done
echo "ALL DONE $MODEL"
