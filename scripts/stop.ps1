$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath 'data/server.pid')) { throw 'No server PID was recorded by start.ps1.' }
$serverPid = [int](Get-Content -LiteralPath 'data/server.pid' -Raw).Trim()
$serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$serverPid" -ErrorAction SilentlyContinue
$expectedPython = (Resolve-Path -LiteralPath '.venv/Scripts/python.exe').Path
if (-not $serverProcess) { Write-Output 'The recorded server is already stopped.'; exit 0 }
if (-not $serverProcess.CommandLine.Contains($expectedPython) -or -not $serverProcess.CommandLine.Contains('uvicorn backend.app:app')) { throw 'The recorded PID no longer matches this project server. No process was stopped.' }
& taskkill.exe /PID $serverPid /T /F | Out-Null
Write-Output 'Prompt Pop server stopped.'
