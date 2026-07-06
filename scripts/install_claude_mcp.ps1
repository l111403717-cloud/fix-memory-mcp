param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$serverPath = Join-Path $projectRoot "scripts\fix_memory_mcp.py"
$dataPath = Join-Path $projectRoot "data"

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $pythonCommand = Get-Command python.exe -ErrorAction Stop
    $PythonPath = $pythonCommand.Source
}

if (-not (Test-Path $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw "Cannot find claude command. Open the same PowerShell where 'claude' works, then run this script again."
}

Write-Host "Python: $PythonPath"
Write-Host "Server: $serverPath"
Write-Host "Data:   $dataPath"

try {
    claude mcp remove mcpServers *> $null
} catch {
    Write-Host "No stale mcpServers entry to remove."
}

try {
    claude mcp remove fix-memory *> $null
} catch {
    Write-Host "No existing fix-memory entry to remove."
}

claude mcp add `
    --env "FIX_MEMORY_ROOT=$dataPath" `
    --transport stdio `
    --scope user `
    fix-memory `
    -- `
    "$PythonPath" `
    "$serverPath"

claude mcp list

Write-Host ""
Write-Host "Done. Restart Claude Code, then run /mcp."
