$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw 'Build the frontend first: npm.cmd --prefix frontend run build' }
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Create the Python environment as described in README.md.' }
New-Item -ItemType Directory -Force -Path 'data' | Out-Null
$pythonPath = (Resolve-Path -LiteralPath '.venv/Scripts/python.exe').Path
$serverArguments = @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000','--workers','1')
if (Test-Path -LiteralPath '.env') { $serverArguments += @('--env-file','.env') }
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { Write-Output 'Port 8000 is already in use. Open http://127.0.0.1:8000 or stop that server before starting another.'; exit 0 }
$serverProcess = Start-Process -FilePath $pythonPath -ArgumentList $serverArguments -WorkingDirectory (Get-Location).Path -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data/server.log' -RedirectStandardError 'data/server-error.log'
Set-Content -LiteralPath 'data/server.pid' -Value $serverProcess.Id
Write-Output 'Prompt Pop started at http://127.0.0.1:8000. Organizer credentials are in local-access.txt if generated during initial setup.'
