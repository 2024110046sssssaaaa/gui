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
    [string]$AppiumHost = "127.0.0.1",
    [int]$AppiumPort = 4723,
    [string]$AppiumBin = "",
    [int]$AppiumStartupTimeout = 60,
    [string]$AppiumLogDir = "",
    [switch]$NoManageAppium,
    [switch]$KeepAppium,
    [switch]$First10FalsePositiveSimple,
    [switch]$AttackSimpletestOnly
)

$ErrorActionPreference = "Continue"

function Test-AppiumStatus {
    param(
        [string]$HostName,
        [int]$Port
    )

    $urls = @(
        "http://${HostName}:$Port/status",
        "http://${HostName}:$Port/wd/hub/status"
    )

    foreach ($url in $urls) {
        try {
            $null = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 2 -ErrorAction Stop
            return [pscustomobject]@{
                Ready = $true
                Url = $url
            }
        } catch {
            continue
        }
    }

    return [pscustomobject]@{
        Ready = $false
        Url = ""
    }
}

function Resolve-AppiumBin {
    param([string]$RequestedBin)

    if ($RequestedBin) {
        return $RequestedBin
    }
    if ($env:APPIUM_BIN) {
        return $env:APPIUM_BIN
    }
    if ($env:APPDATA) {
        $npmAppium = Join-Path $env:APPDATA "npm\appium.cmd"
        if (Test-Path $npmAppium) {
            return $npmAppium
        }
    }
    return "appium"
}

function Start-ManagedAppium {
    param(
        [string]$HostName,
        [int]$Port,
        [string]$RequestedBin,
        [int]$StartupTimeout,
        [string]$LogDir,
        [string]$Root
    )

    $status = Test-AppiumStatus -HostName $HostName -Port $Port
    if ($status.Ready) {
        Write-Output "APPIUM_STATUS=reuse $($status.Url)"
        return [pscustomobject]@{
            Owned = $false
            Process = $null
            Url = $status.Url
            Stdout = ""
            Stderr = ""
        }
    }

    $resolvedBin = Resolve-AppiumBin -RequestedBin $RequestedBin
    if (-not $LogDir) {
        $LogDir = Join-Path $Root "logs"
    }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $stdoutPath = Join-Path $LogDir ("appium_{0}_{1}.out.log" -f $Port, $ts)
    $stderrPath = Join-Path $LogDir ("appium_{0}_{1}.err.log" -f $Port, $ts)
    $args = @("--address", $HostName, "--port", "$Port", "--log-level", "info")

    Write-Output "APPIUM_STATUS=start $resolvedBin $($args -join ' ')"
    try {
        $process = Start-Process `
            -FilePath $resolvedBin `
            -ArgumentList $args `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -PassThru `
            -WindowStyle Hidden `
            -ErrorAction Stop
    } catch {
        throw "Failed to start Appium. Install Appium or set -AppiumBin / APPIUM_BIN. Detail: $($_.Exception.Message)"
    }

    $deadline = (Get-Date).AddSeconds($StartupTimeout)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 1
        if ($process.HasExited) {
            $tail = ""
            if (Test-Path $stderrPath) {
                $tail = (Get-Content -Path $stderrPath -Tail 30 -ErrorAction SilentlyContinue) -join "`n"
            }
            throw "Appium exited before ready. stderr tail:`n$tail"
        }

        $status = Test-AppiumStatus -HostName $HostName -Port $Port
        if ($status.Ready) {
            Write-Output "APPIUM_STATUS=ready $($status.Url)"
            return [pscustomobject]@{
                Owned = $true
                Process = $process
                Url = $status.Url
                Stdout = $stdoutPath
                Stderr = $stderrPath
            }
        }
    }

    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    $tail = ""
    if (Test-Path $stderrPath) {
        $tail = (Get-Content -Path $stderrPath -Tail 30 -ErrorAction SilentlyContinue) -join "`n"
    }
    throw "Timed out waiting for Appium on ${HostName}:$Port. stderr tail:`n$tail"
}

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
$env:APPIUM_HOST = $AppiumHost
$env:APPIUM_PORT = "$AppiumPort"
$env:MOBILE_SAFETY_MANAGE_APPIUM = "0"
if ($AppiumBin) {
    $env:APPIUM_BIN = $AppiumBin
}
if ($AppiumLogDir) {
    $env:APPIUM_LOG_DIR = $AppiumLogDir
}

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
Write-Output "APPIUM_MANAGED=$(-not $NoManageAppium)"
Write-Output "APPIUM_CHILD_RUNNER_MANAGED=$env:MOBILE_SAFETY_MANAGE_APPIUM"
Write-Output "APPIUM_HOST=$AppiumHost"
Write-Output "APPIUM_PORT=$AppiumPort"
if ($AppiumBin) {
    Write-Output "APPIUM_BIN=$AppiumBin"
}
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

$managedAppium = $null

try {
    if (-not $NoManageAppium) {
        $managedAppium = Start-ManagedAppium `
            -HostName $AppiumHost `
            -Port $AppiumPort `
            -RequestedBin $AppiumBin `
            -StartupTimeout $AppiumStartupTimeout `
            -LogDir $AppiumLogDir `
            -Root $ProjectRoot
        if ($managedAppium.Stdout) {
            Write-Output "APPIUM_STDOUT=$($managedAppium.Stdout)"
            Write-Output "APPIUM_STDERR=$($managedAppium.Stderr)"
        }
    } else {
        Write-Output "APPIUM_STATUS=disabled"
    }

    foreach ($dataset in $datasets) {
        Write-Output "===== DATASET $($dataset.FullName) ====="
        if ($Mode -eq "fp") {
            & $PythonPath $runner `
                --dataset $dataset.FullName `
                --start $Start `
                --count $Count `
                --model $Model `
                --port $AdbPort `
                --max-steps $MaxSteps `
                --api-timeout $ApiTimeout
        } else {
            & $PythonPath $runner `
                --dataset $dataset.FullName `
                --start $Start `
                --count $Count `
                --model $Model `
                --port $AdbPort `
                --max-steps $MaxSteps
        }
        $exitCode = $LASTEXITCODE
        Write-Output "===== DONE $($dataset.Name) exit=$exitCode ====="
    }
} finally {
    if ($managedAppium -and $managedAppium.Owned -and -not $KeepAppium -and $managedAppium.Process) {
        Write-Output "APPIUM_STATUS=stop owned process $($managedAppium.Process.Id)"
        Stop-Process -Id $managedAppium.Process.Id -Force -ErrorAction SilentlyContinue
    } elseif ($managedAppium -and $managedAppium.Owned -and $KeepAppium) {
        Write-Output "APPIUM_STATUS=keep owned process $($managedAppium.Process.Id)"
    }

    Write-Output "===== MOBILE GUARD PORTABLE RUN END ====="
}
