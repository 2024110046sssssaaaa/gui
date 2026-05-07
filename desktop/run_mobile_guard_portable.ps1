param(
    [ValidateSet("attack", "fp")]
    [string]$Mode = "attack",
    [string]$Model = "qwen-vl-max-latest",
    [int]$Start = 0,
    [int]$Count = 10,
    [int]$MaxSteps = 8,
    [int]$ApiTimeout = 90,
    [int]$AdbPort = 5554,
    [string]$ProjectRoot = "D:\datasets\MobileSafetyBench",
    [string]$PythonPath = "python",
    [string]$DatasetRoot = "",
    [string]$ResultRoot = "",
    [string]$DefensePrompt = "",
    [string]$GuardLevel = "strict",
    [string]$UseTaskMetadata = "0",
    [string]$JudgeModel = "qwen-vl-max-latest",
    [string]$JudgeBaseUrl = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    [string]$OpenAIBaseUrl = "",
    [string]$ThirdPartyProxyBaseUrl = "",
    [string]$ThirdPartyProxyApiKey = "",
    [switch]$First10FalsePositiveSimple,
    [switch]$AttackSimpletestOnly
)

$ErrorActionPreference = "Continue"
Set-Location $ProjectRoot

if (-not $DefensePrompt) {
    $DefensePrompt = Join-Path $ProjectRoot "mobile_safety\prompt\asb_mobile_guard_defense_prompt.json"
}

if (-not (Test-Path $DefensePrompt)) {
    throw "Defense prompt not found: $DefensePrompt"
}

if (-not $DatasetRoot) {
    if ($Mode -eq "fp") {
        if ($First10FalsePositiveSimple) {
            $DatasetRoot = Join-Path $ProjectRoot "attacks\false_positive_simple"
        } else {
            $DatasetRoot = Join-Path $ProjectRoot "attacks\false_positive"
        }
    } else {
        $DatasetRoot = Join-Path $ProjectRoot "attacks"
    }
}

if (-not $ResultRoot) {
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    if ($Mode -eq "fp") {
        $ResultRoot = Join-Path $ProjectRoot ("result_{0}_asb_mobile_guard_fp_{1}" -f ($Model -replace "[^A-Za-z0-9._-]", "_"), $ts)
    } else {
        $ResultRoot = Join-Path $ProjectRoot ("result_{0}_asb_mobile_guard_attack_{1}" -f ($Model -replace "[^A-Za-z0-9._-]", "_"), $ts)
    }
}

New-Item -ItemType Directory -Force -Path $ResultRoot | Out-Null

$env:MOBILE_SAFETY_HOME = $ProjectRoot
$env:ANDROID_HOME = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { "D:\sdk" }
$env:ANDROID_SDK_ROOT = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { $env:ANDROID_HOME }
$env:MOBILE_SAFETY_DEFENSE_PROMPT_FILE = $DefensePrompt
$env:MOBILE_SAFETY_GUARD_LEVEL = $GuardLevel
$env:MOBILE_SAFETY_GUARD_USE_TASK_METADATA = $UseTaskMetadata

if ($ThirdPartyProxyBaseUrl) {
    $env:THIRD_PARTY_PROXY_BASE_URL = $ThirdPartyProxyBaseUrl
}
if ($ThirdPartyProxyApiKey) {
    $env:THIRD_PARTY_PROXY_API_KEY = $ThirdPartyProxyApiKey
    $env:OPENAI_COMPATIBLE_FORCE_RAW_AUTH = "1"
}
if ($OpenAIBaseUrl) {
    $env:OPENAI_BASE_URL = $OpenAIBaseUrl
}

if ($Mode -eq "fp") {
    $env:FALSE_POSITIVE_RESULT_ROOT = $ResultRoot
    $env:FP_JUDGE_MODEL = $JudgeModel
    $env:FP_JUDGE_BASE_URL = $JudgeBaseUrl
    $runner = "attacks\quick_test_adb_fp.py"
    $filter = "*_false_positive.json"
    $datasets = Get-ChildItem $DatasetRoot -Recurse -Filter $filter | Sort-Object FullName
} else {
    $env:SIMPLETEST_RESULT_ROOT = $ResultRoot
    $runner = "attacks\quick_test_adb.py"
    $datasets = Get-ChildItem $DatasetRoot -Recurse -Filter "*_simpletest.json" |
        Where-Object {
            $_.FullName -notmatch "false_positive" -and
            $_.FullName -notmatch "writerready" -and
            $_.FullName -notmatch "shadow"
        } |
        Sort-Object FullName
    if (-not $AttackSimpletestOnly) {
        Write-Warning "This portable script is intended for *_simpletest.json attack datasets. Use -AttackSimpletestOnly to acknowledge that mode."
    }
}

Write-Output "===== MOBILE GUARD PORTABLE RUN START ====="
Write-Output "MODE=$Mode"
Write-Output "PROJECT_ROOT=$ProjectRoot"
Write-Output "DATASET_ROOT=$DatasetRoot"
Write-Output "RESULT_ROOT=$ResultRoot"
Write-Output "RUNNER=$runner"
Write-Output "MODEL=$Model"
Write-Output "START=$Start"
Write-Output "COUNT=$Count"
Write-Output "MAX_STEPS=$MaxSteps"
Write-Output "API_TIMEOUT=$ApiTimeout"
Write-Output "ADB_PORT=$AdbPort"
Write-Output "DEFENSE_PROMPT=$DefensePrompt"
Write-Output "GUARD_LEVEL=$GuardLevel"
Write-Output "GUARD_USE_METADATA=$UseTaskMetadata"
Write-Output "DATASET_COUNT=$($datasets.Count)"

if ($Mode -eq "fp") {
    Write-Output "FP_JUDGE_MODEL=$JudgeModel"
    Write-Output "FP_JUDGE_BASE_URL=$JudgeBaseUrl"
}
if ($ThirdPartyProxyBaseUrl) {
    Write-Output "THIRD_PARTY_PROXY_BASE_URL=$ThirdPartyProxyBaseUrl"
}
if ($OpenAIBaseUrl) {
    Write-Output "OPENAI_BASE_URL=$OpenAIBaseUrl"
}

foreach ($dataset in $datasets) {
    Write-Output "===== DATASET $($dataset.FullName) ====="
    & $PythonPath $runner `
        --dataset $dataset.FullName `
        --start $Start `
        --count $Count `
        --model $Model `
        --port $AdbPort `
        --max-steps $MaxSteps `
        --api-timeout $ApiTimeout
    $exitCode = $LASTEXITCODE
    Write-Output "===== DONE $($dataset.Name) exit=$exitCode ====="
}

Write-Output "===== MOBILE GUARD PORTABLE RUN END ====="
