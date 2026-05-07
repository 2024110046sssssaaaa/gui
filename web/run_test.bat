@echo off
chcp 65001 >nul
setlocal

set GITLAB=http://localhost:8023
set REDDIT=http://localhost:9999
set DATASET=webarena
if "%OPENAI_API_KEY%"=="" echo Warning: OPENAI_API_KEY is not set.
set OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

cd /d "d:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections"

echo Running unified_runner.py with example config...
echo.
echo Environment Variables:
echo GITLAB=%GITLAB%
echo REDDIT=%REDDIT%
echo OPENAI_API_BASE=%OPENAI_API_BASE%
echo.

call venv\Scripts\python.exe unified_runner.py --unified-config configs/unified_benchmark.example.json --output-root C:\tmp\wasp-test-gitlab --model qwen --gitlab-domain "http://localhost:8023" --reddit-domain "http://localhost:9999"

echo.
echo Done!
pause
