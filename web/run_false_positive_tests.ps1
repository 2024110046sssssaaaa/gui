# Run false positive tests - PowerShell version
# 设置环境变量
$env:GITLAB = "http://localhost:8023"
$env:REDDIT = "http://localhost:9999"
$env:DATASET = "webarena"
if (-not $env:OPENAI_API_KEY) { Write-Warning "OPENAI_API_KEY is not set; set it in your local shell before running." }
$env:OPENAI_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 工作目录
Set-Location "d:\桌面\安全数据\web端\wasp-main-all\visualwebarena"

# 运行测试命令 - 测试 browserart_attacks_fixed (10个样本, task_id 3080-3089)
Write-Host "Running false positive tests for browserart_attacks_fixed..." -ForegroundColor Cyan
python run.py `
    --test_config_base_dir "d:\桌面\安全数据\web端\wasp-main-all\test_output\samples_false_positive\browserart_attacks_fixed\webarena_tasks_attacker" `
    --result_dir "d:\桌面\安全数据\web端\wasp-main-all\test_output\results_false_positive\browserart_attacks_fixed" `
    --provider openai `
    --model qwen-plus `
    --max_steps 20 `
    --test_start_idx 0 `
    --test_end_idx 10 `
    --action_set_tag id_accessibility_tree `
    --observation_type accessibility_tree `
    --current_viewport_only
