$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = if ($env:CLIPPER_PYTHON) { $env:CLIPPER_PYTHON } else { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $python)) { throw 'Najpierw utwórz .venv (python -m venv .venv).' }

& $python -m pip install --quiet setuptools==70.2.0 wheel==0.45.1
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zainstalować narzędzi budowania.' }
& $python -m pip install --quiet --no-build-isolation -r requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zainstalować zależności desktopowych.' }

$node = (Get-Command node.exe -ErrorAction Stop).Source
$ffmpeg = (Get-Command ffmpeg.exe -ErrorAction Stop).Source

& $python -m PyInstaller --noconfirm --clean --onedir --windowed --name 'YouTube Clipper' --icon 'installer\YouTube Clipper.ico' `
  --collect-all yt_dlp --collect-all webview `
  --add-data 'web:web' `
  --add-data 'third_party:third_party' `
  --add-binary "${node}:tools" `
  --add-binary "${ffmpeg}:tools" `
  desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zbudować YouTube Clipper.exe.' }

$iscc = @(
  (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
  (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
  (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) {
  Write-Warning 'Brak Inno Setup 6. Aplikacja przenośna jest gotowa w dist\YouTube Clipper\YouTube Clipper.exe; instalator wymaga ISCC.exe.'
  exit 0
}
$compileOutput = & $iscc 'installer\YouTube Clipper.iss' 2>&1
if ($LASTEXITCODE -ne 0) {
  $compileOutput | Select-Object -Last 30
  throw 'Nie udało się zbudować instalatora.'
}
$compileOutput | Select-Object -Last 4
