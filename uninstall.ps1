<#
.SYNOPSIS
    Stops any running Ultra Dimmer process and removes Desktop/Start Menu/Startup shortcuts.
#>

$ErrorActionPreference = "SilentlyContinue"

# Gracefully stop running Ultra Dimmer pythonw processes so atexit/cleanup restores 100% display
$Running = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -match "ultra_dimmer\.pyw" -or $_.CommandLine -match "UltraDimmer\.pyw")
}
foreach ($Proc in $Running) {
    Stop-Process -Id $Proc.ProcessId -Force
    Write-Host "[OK] Stopped running Ultra Dimmer process (PID $($Proc.ProcessId))."
}

$Paths = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Ultra Dimmer.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "Ultra Dimmer.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Startup")) "Ultra Dimmer.lnk")
)

foreach ($Path in $Paths) {
    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Force
        Write-Host "[OK] Removed shortcut: $Path"
    }
}

Write-Host ""
Write-Host "Ultra Dimmer uninstalled cleanly."
