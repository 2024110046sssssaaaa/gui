import os

# ============================================================
#  API Key 配置（必须设置，否则模型无法调用）
# ============================================================
# vLLM 自托管（Qwen2.5-VL-7B-Instruct 等）:
#   → 在 Windows PowerShell:  $env:VLLM_BASE_URL="http://<服务器IP>:8080/v1"
#   →                    $env:VLLM_MODEL="Qwen2.5-VL-7B-Instruct"
#
# 千问 / DashScope（qwen-vl-max 等）:  $env:DASHSCOPE_API_KEY="sk-xxx"
#   → 在 Windows PowerShell:  $env:DASHSCOPE_API_KEY="你的key"
#   → 或在系统环境变量中新建 DASHSCOPE_API_KEY
#
# aaaapi.com（gpt-5.1 等）:  $env:OPENAI_API_KEY="xxx" + $env:OPENAI_API_BASE="https://api.aaaapi.com/v1"
# Anthropic（claude 等）:  $env:ANTHROPIC_API_KEY="sk-ant-xxx"
# ============================================================

# ============================================================
# 集中配置文件 —— 修改这里即可选择要测试的内容
# 用法: python run.py
# ============================================================

# 【第一步】模型配置
# ============================================================
# vLLM 自托管（需先在远程服务器启动 vLLM server）:
#   MODEL = "Qwen2.5-VL-7B-Instruct"
#   并设置环境变量 VLLM_BASE_URL 和 VLLM_MODEL
#
# DashScope 云端:
#   MODEL = "qwen-vl-max"
#   需要 DASHSCOPE_API_KEY
# ============================================================
MODEL = "Qwen2.5-VL-7B-Instruct"
JUDGE_MODEL = "qwen-vl-max"
TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 4000

# 【第二步】选择测试配置文件
# ============================================================
# - "test_0319.json"              → chrome (15个)
# - "test_misuse.json"            → 10个 domain, 60个任务
# - "test_misbehavior.json"       → 10个 domain, 50个任务
# - "test_injection.json"         → 5个 domain, 10个任务
# - "test_multiapps_selected5.json"   → multi_apps, 5个任务
# - "test_multiapps_selected5x5.json" → multi_apps, 25个任务
# - "test_riosworld.json"         → 4个 domain, 22个任务
# - "test_osworld_small.json"     → 10个 domain, 39个任务
# - "test_osworld_all.json"       → 10个 domain, 369个任务
# - "test_x08.json"               → X08跨平台QR攻击, chrome domain, 100个任务
# - "test_benign.json"            → benign 任务, 9个 domain, 测试Agent安全性
# - "test_false_positive.json"    → false_positive任务, 10个domain, 测试假阳性识别
# - "test_examples_simple.json"    → examples_simple, 简单示例
# ============================================================
TEST_CONFIG = "test_false_positive.json"

# 【第三步】限制只运行某个 domain（None 表示全部）
# ============================================================
# None        → 运行 TEST_CONFIG 中的所有 domain
# "multi_apps" → 只运行 multi_apps
# "vlc"        → 只运行 vlc
# "os"         → 只运行 os
# "chrome"    → 只运行 chrome（X08 在 chrome domain）
# "benign"    → 运行所有 benign 任务
# "false_positive" → 运行所有 false_positive 任务
# "examples_simple" → 运行 examples_simple
# ============================================================
DOMAIN_FILTER = "all"

# 【第四步】结果目录
# ============================================================
# 程序会自动拼接为 results/{MODEL}/{RESULT_DIR_SUFFIX}/
RESULT_DIR_SUFFIX = "Qwen2.5-VL-7B_false_positive_test"

# 【第五步】VM 和环境配置
# ============================================================
VM_PATH = os.environ.get("GUIHAZARD_VM_PATH", "C:\\path\\to\\Ubuntu.vmx")
# OS type of the VM: "Ubuntu" | "Windows" | "MacOS"
OS_TYPE = "Ubuntu"
HEADLESS = False
MAX_STEPS = 3

# 【第六步】数据目录（os-harm-all 下的 evaluation_examples）
# ============================================================
TEST_CONFIG_BASE_DIR = os.environ.get("GUIHAZARD_TEST_CONFIG_BASE_DIR", "C:\\path\\to\\evaluation_examples")
TEST_CONFIG_EXAMPLES_SUBDIR = "false_positive"
