<#
  Cài Open-LLM-VTuber + nhân vật Anna (tiếng Việt, chạy offline) trên Windows.
  Làm theo hướng dẫn chính thức: https://docs.llmvtuber.com/en/docs/quick-start

  Cách chạy (mở PowerShell trong thư mục AnnaLite):
      powershell -ExecutionPolicy Bypass -File scripts\cai_open_llm_vtuber.ps1

  Tùy chọn:
      -InstallDir D:\AI\Open-LLM-VTuber   Thư mục cài (KHÔNG dùng chữ có dấu / tiếng Trung)
      -Model qwen3.5:4b                   Model Ollama muốn dùng (mặc định: anna-qwen)
      -Lan                                Cho điện thoại cùng Wi-Fi mở được giao diện

  Chạy lại script nhiều lần cũng không sao: bước nào xong rồi sẽ được bỏ qua.
#>
param(
    [string]$InstallDir = (Join-Path $HOME 'Open-LLM-VTuber'),
    [string]$Model = 'anna-qwen',
    [switch]$Lan
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest trên PowerShell 5.1 chạy nhanh hơn nhiều
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$AnnaLite = Split-Path -Parent $PSScriptRoot
$ApplyScript = Join-Path $AnnaLite 'integrations\open-llm-vtuber\apply_anna.py'
$PiperBase = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/'
$PiperVoice = 'vi_VN-vais1000-medium'

function Step([string]$msg) { Write-Host ''; Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok([string]$msg) { Write-Host "    $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "    [!] $msg" -ForegroundColor Yellow }
function Fail([string]$msg) {
    Write-Host ''
    Write-Host "[LỖI] $msg" -ForegroundColor Red
    Write-Host 'Chụp màn hình lỗi này gửi cho Claude nhé.' -ForegroundColor Red
    exit 1
}
function Has([string]$cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Update-PathFromSystem {
    # Sau khi winget cài xong, cửa sổ hiện tại chưa thấy lệnh mới -> nạp lại PATH
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
    $extra = @(
        (Join-Path $HOME '.local\bin'),                                  # uv
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links')           # ffmpeg từ winget
    )
    foreach ($p in $extra) { if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) { $env:Path = "$p;$env:Path" } }
}

function Invoke-Native([string]$exe, [string[]]$arguments) {
    # Chạy lệnh ngoài (git, uv, winget...) và dừng ngay nếu lệnh báo lỗi
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { Fail "Lệnh bị lỗi (mã $LASTEXITCODE): $exe $($arguments -join ' ')" }
}

function Install-IfMissing([string]$cmd, [string]$wingetId, [string]$name) {
    if (Has $cmd) { Ok "$name đã có sẵn"; return }
    if (-not (Has 'winget')) { Fail "Không có winget để cài $name. Cài 'App Installer' từ Microsoft Store rồi chạy lại." }
    Write-Host "    Đang cài $name..."
    Invoke-Native 'winget' @('install', '--id', $wingetId, '-e', '--accept-source-agreements', '--accept-package-agreements')
    Update-PathFromSystem
    if (-not (Has $cmd)) { Fail "Đã cài $name nhưng chưa thấy lệnh '$cmd'. Đóng PowerShell, mở lại rồi chạy lại script." }
    Ok "Đã cài $name"
}

# ---------------------------------------------------------------------------
Step '0. Kiểm tra'
if ($InstallDir -match '[^\x00-\x7F]') {
    Fail "Đường dẫn '$InstallDir' có chữ có dấu, Open-LLM-VTuber sẽ lỗi. Dùng -InstallDir với đường dẫn không dấu, ví dụ D:\AI\Open-LLM-VTuber"
}
if (-not (Test-Path $ApplyScript)) { Fail "Không thấy $ApplyScript. Hãy chạy script này từ trong thư mục AnnaLite." }
Ok "Thư mục cài: $InstallDir"
Ok "Model: $Model"
Update-PathFromSystem

# ---------------------------------------------------------------------------
Step '1. Cài Git, FFmpeg, uv (nếu chưa có)'
Install-IfMissing 'git' 'Git.Git' 'Git'
Install-IfMissing 'ffmpeg' 'Gyan.FFmpeg' 'FFmpeg'
Install-IfMissing 'uv' 'astral-sh.uv' 'uv'
Ok 'Không cần cài CUDA Toolkit / cuDNN: Ollama đã kèm sẵn phần chạy GPU, còn nghe/nói chạy bằng CPU.'

# ---------------------------------------------------------------------------
Step '2. Kiểm tra Ollama và model'
if (-not (Has 'ollama')) {
    Fail 'Chưa có Ollama. Tải ở https://ollama.com/download, cài xong chạy lại script.'
}
# PowerShell 5.1: chuyển hướng stderr của lệnh ngoài khi đang để 'Stop' sẽ làm script dừng hẳn,
# nên tạm hạ xuống 'Continue' lúc hỏi Ollama.
$models = ''
$ollamaOk = $false
$prevPref = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $models = (& ollama list 2>$null) -join "`n"
    $ollamaOk = ($LASTEXITCODE -eq 0)
} catch {
    $ollamaOk = $false
} finally {
    $ErrorActionPreference = $prevPref
}
if (-not $ollamaOk) {
    Warn 'Không hỏi được Ollama. Hãy mở app Ollama (biểu tượng con lạc đà ở khay hệ thống) rồi chạy lại.'
}
$pattern = '(?m)^' + [regex]::Escape($Model) + '(:latest)?\s'
if ($models -match $pattern) {
    Ok "Ollama đã có model $Model"
} elseif ($Model -eq 'anna-qwen' -and (Test-Path (Join-Path $AnnaLite 'models\anna-qwen-Q4_K_M.gguf'))) {
    Write-Host '    Đang tạo model anna-qwen từ file GGUF...'
    Push-Location $AnnaLite
    try { Invoke-Native 'ollama' @('create', 'anna-qwen', '-f', 'Modelfile') } finally { Pop-Location }
    Ok 'Đã tạo model anna-qwen'
} else {
    Warn "Ollama chưa có model '$Model'. Cài vẫn tiếp tục, nhưng trước khi chạy hãy:"
    Warn '  - Có file models\anna-qwen-Q4_K_M.gguf trong AnnaLite rồi: ollama create anna-qwen -f Modelfile'
    Warn '  - Hoặc dùng tạm model chính thức: ollama pull qwen3.5:4b, rồi chạy lại script với -Model qwen3.5:4b'
}

# ---------------------------------------------------------------------------
Step '3. Tải mã nguồn Open-LLM-VTuber'
if (Test-Path (Join-Path $InstallDir '.git')) {
    Ok 'Đã có, kiểm tra phần giao diện (frontend)...'
    Invoke-Native 'git' @('-C', $InstallDir, 'submodule', 'update', '--init', '--recursive')
} else {
    # --recursive là BẮT BUỘC, thiếu nó web sẽ báo {"detail":"Not Found"}
    Invoke-Native 'git' @('clone', 'https://github.com/Open-LLM-VTuber/Open-LLM-VTuber', '--recursive', $InstallDir)
}
Ok 'Xong'

Push-Location $InstallDir
try {
    # -----------------------------------------------------------------------
    Step '4. Cài thư viện Python (lần đầu khá lâu, có thể 5-15 phút)'
    Invoke-Native 'uv' @('sync')
    Write-Host '    Thêm bộ nghe tiếng Việt (faster-whisper) và giọng nói offline (piper-tts)...'
    Invoke-Native 'uv' @('add', 'faster-whisper', 'piper-tts')
    Ok 'Xong'

    # -----------------------------------------------------------------------
    Step '5. Tải giọng nói tiếng Việt (Piper)'
    $voiceDir = Join-Path $InstallDir 'models\piper'
    New-Item -ItemType Directory -Force -Path $voiceDir | Out-Null
    foreach ($file in @("$PiperVoice.onnx", "$PiperVoice.onnx.json")) {
        $dest = Join-Path $voiceDir $file
        if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 0)) { Ok "$file đã có"; continue }
        try {
            Write-Host "    Đang tải $file..."
            Invoke-WebRequest -Uri ($PiperBase + $file + '?download=true') -OutFile $dest -UseBasicParsing
            Ok "Đã tải $file"
        } catch {
            if (Test-Path $dest) { Remove-Item $dest -Force }
            Warn "Không tải được $file ($($_.Exception.Message))."
            Warn "Tải tay ở $PiperBase rồi bỏ vào $voiceDir"
        }
    }

    # -----------------------------------------------------------------------
    Step '6. Đưa Anna vào conf.yaml (Anna thành nhân vật mặc định)'
    $applyArgs = @('run', 'python', $ApplyScript, '.', '--model', $Model)
    if ($Lan) { $applyArgs += '--lan' }
    Invoke-Native 'uv' $applyArgs
} finally {
    Pop-Location
}

# ---------------------------------------------------------------------------
Step 'XONG! Cách chạy Anna VTuber:'
Write-Host "    cd `"$InstallDir`""
Write-Host '    uv run run_server.py'
Write-Host ''
Write-Host '    Đợi tới khi thấy dòng "Uvicorn running on ..." rồi mở Chrome: http://localhost:12393'
Write-Host '    Lần chạy đầu sẽ tự tải model nghe giọng Whisper (~500 MB), cần có mạng.'
if ($Lan) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -First 1).IPAddress
    if ($ip) { Write-Host "    Trên điện thoại (cùng Wi-Fi), mở Chrome: http://${ip}:12393" }
    Write-Host '    Windows hỏi tường lửa thì bấm Allow.'
}
