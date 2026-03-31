param(
  [string]$PythonExe = "python",
  [int]$Port = 8765,
  [string]$Token = "scienceclaw-local-bridge",
  [string[]]$HostReadRoots = @()
)

$env:SC_OBSIDIAN_BRIDGE_HOST = "127.0.0.1"
$env:SC_OBSIDIAN_BRIDGE_PORT = "$Port"
$env:SC_OBSIDIAN_BRIDGE_TOKEN = $Token

if ($HostReadRoots.Count -gt 0) {
  $pathSep = [System.IO.Path]::PathSeparator
  $joinedRoots = ($HostReadRoots | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() }) -join $pathSep
  $env:SC_HOST_READ_ROOTS = $joinedRoots
}
else {
  Remove-Item Env:SC_HOST_READ_ROOTS -ErrorAction SilentlyContinue
}

Write-Host "ScienceClaw Obsidian host bridge starting..."
Write-Host "  Host: $($env:SC_OBSIDIAN_BRIDGE_HOST)"
Write-Host "  Port: $Port"
Write-Host "  Token: $Token"
if ($env:SC_HOST_READ_ROOTS) {
  Write-Host "  SC_HOST_READ_ROOTS: $($env:SC_HOST_READ_ROOTS)"
}
else {
  Write-Warning "SC_HOST_READ_ROOTS is not set. Host-side PDF/HTML attachment reads will be rejected."
}

& $PythonExe "$PSScriptRoot\obsidian_host_bridge.py"
