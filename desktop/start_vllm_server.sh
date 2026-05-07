#!/bin/bash
# ============================================================
# vLLM Server 启动脚本
# 运行在远程服务器: ssh -p 40022 zenglingfeng@10.2.170.120
# ============================================================

set -e

# --- 配置参数（按需修改）---
MODEL_PATH="/nfsdata-117/model/Qwen2.5-VL-7B-Instruct"
PORT=8080
TP=1  # Tensor Parallel（7B模型单卡即可，用 TP=1）
MAX_MODEL_LEN=8192
GPU_MEMORY_UTILIZATION=0.90
# --------------------------------

CONDA_ENV="qwen3-vllm"
PYTHON="/nfsdata-117/miniconda3/envs/${CONDA_ENV}/bin/python"

echo "[$(date)] Starting vLLM server..."
echo "  Model:   $MODEL_PATH"
echo "  Port:    $PORT"
echo "  TP:      $TP"
echo "  MaxLen:  $MAX_MODEL_LEN"

$PYTHON -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --served-model-name "Qwen2.5-VL-7B-Instruct" \
    --port $PORT \
    --tensor-parallel-size $TP \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --trust-remote-code \
    --limit-mm-per-prompt image=8 \
    --enforce-eager \
    2>&1 | tee vllm_server.log

