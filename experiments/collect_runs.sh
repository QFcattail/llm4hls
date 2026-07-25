#!/usr/bin/env bash
# collect_runs.sh - 把服务器上的测试产物归档回本机 experiments/
# 用法: ./collect_runs.sh <model_dir> [<model_dir>...]
#   例: ./collect_runs.sh qwen3.6-27b qwen3.5-122b-a10b deepseek-v4-pro
# 每个模型目录下的每个任务归档 transcript/scores/final kernel/csynth.xml/ppa.json
# prompts.jsonl 全量归档（逐条 prompt 是报告附录 B 的数据源）。
set -e
cd "$(dirname "$0")"
SERVER="QFS-STATION"
REMOTE="/home/admin/fpga-agent/runs"

for MODEL in "$@"; do
  TASKS=$(ssh -o BatchMode=yes "$SERVER" "ls $REMOTE/$MODEL/ 2>/dev/null")
  for T in $TASKS; do
    DST="$MODEL/$T"
    mkdir -p "$DST"
    echo "== archiving $MODEL/$T -> experiments/$DST"
    # 关键小文件
    rsync -az --ignore-existing \
      "$SERVER:$REMOTE/$MODEL/$T/transcript.txt" \
      "$SERVER:$REMOTE/$MODEL/$T/scores.jsonl" \
      "$SERVER:$REMOTE/$MODEL/$T/ppa.json" \
      "$DST/" 2>/dev/null || true
    rsync -az --ignore-existing \
      "$SERVER:$REMOTE/$MODEL/$T/${T}.jsonl" \
      "$SERVER:$REMOTE/$MODEL/$T/${T}_prompts.jsonl" \
      "$DST/" 2>/dev/null || true
    rsync -az --ignore-existing --include='final_*' --exclude='*' \
      "$SERVER:$REMOTE/$MODEL/$T/" "$DST/" 2>/dev/null || true
    # grade 目录只收 csynth.xml（PPA 数据源）
    rsync -az --ignore-existing --include='*/' --include='csynth.xml' --exclude='*' \
      "$SERVER:$REMOTE/$MODEL/$T/grade/" "$DST/grade/" 2>/dev/null || true
  done
done
echo "collect done: $*"
