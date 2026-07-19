param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$serverPath = Join-Path $projectRoot "scripts\fix_memory_mcp.py"
$healthcheckPath = Join-Path $projectRoot "scripts\mcp_healthcheck.py"
$dataPath = Join-Path $projectRoot "data"

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $pythonCommand = Get-Command python.exe -ErrorAction Stop
    $PythonPath = $pythonCommand.Source
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw "Cannot find codex command. Open the same PowerShell where 'codex' works, then run this script again."
}

Write-Host "Python: $PythonPath"
Write-Host "Server: $serverPath"
Write-Host "Data:   $dataPath"

& $PythonPath $healthcheckPath --python $PythonPath --server $serverPath --data $dataPath
if ($LASTEXITCODE -ne 0) {
    throw "Fix Memory MCP health check failed; Codex configuration was not changed."
}

try {
    codex mcp remove fix-memory *> $null
} catch {
    Write-Host "No existing fix-memory entry to remove."
}

codex mcp add `
    --env "FIX_MEMORY_ROOT=$dataPath" `
    fix-memory `
    -- `
    $PythonPath `
    $serverPath

if ($LASTEXITCODE -ne 0) {
    throw "codex mcp add failed."
}

codex mcp list

Write-Host ""
Write-Host "Done. Restart Codex so new tasks can call assemble_context."
