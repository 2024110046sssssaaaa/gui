#!/bin/bash
# Run false positive tests

# 设置环境变量
export GITLAB='http://localhost:8023'
export REDDIT='http://localhost:9999'
export DATASET='webarena'
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export OPENAI_API_BASE='https://dashscope.aliyuncs.com/compatible-mode/v1'

# 工作目录
cd "d:/桌面/安全数据/web端/wasp-main-all/visualwebarena"

# 运行测试命令
python run.py \
    --test_config_base_dir "d:/桌面/安全数据/web端/wasp-main-all/test_output/samples_false_positive/browserart_attacks_fixed/webarena_tasks_attacker" \
    --result_dir "d:/桌面/安全数据/web端/wasp-main-all/test_output/results_false_positive/browserart_attacks_fixed" \
    --provider openai \
    --model qwen-plus \
    --max_steps 20 \
    --test_start_idx 0 \
    --test_end_idx 10 \
    --action_set_tag id_accessibility_tree \
    --observation_type accessibility_tree \
    --current_viewport_only
