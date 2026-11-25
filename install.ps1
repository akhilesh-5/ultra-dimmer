<#
.SYNOPSIS
    Installs Desktop and Start Menu shortcuts for Ultra Dimmer (no Startup auto-run).
#>

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$AppScript = Join-Path $RepoRoot "src\ultra_dimmer.pyw"
$IconPath = Join-Path $RepoRoot "assets\ultra_dimmer.ico"
$IconGen = Join-Path $RepoRoot "assets\generate_icon.py"

if (-not (Test-Path $AppScript)) {
    throw "Could not find application entrypoint: $AppScript"
}

# Locate pythonw.exe (supports Windows Store alias and standard python.org installs)
$PythonwCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if (-not $PythonwCmd) {
    $FallbackPythonw = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\pythonw.exe"
    if (Test-Path $FallbackPythonw) {
        $PythonwPath = $FallbackPythonw
    } else {
        throw "pythonw.exe was not found on PATH. Please install Python 3.10+ with Tkinter."
    }
} else {
    $PythonwPath = $PythonwCmd.Source
}

# Verify Tkinter availability
$PythonCmd = Get-Command python.exe -ErrorAction SilentlyContinue
if ($PythonCmd) {
    & $PythonCmd.Source -c "import tkinter" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python Tkinter module is missing. Please reinstall Python with tcl/tk enabled."
    }
}

# Generate icon asset if absent and Pillow is available
if (-not (Test-Path $IconPath) -and (Test-Path $IconGen) -and $PythonCmd) {
    try {
        & $PythonCmd.Source $IconGen | Out-Null
    } catch {
        Write-Warning "Could not regenerate icon asset; continuing without custom icon."
    }
}

$WshShell = New-Object -ComObject WScript.Shell

$Shortcuts = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Ultra Dimmer.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "Ultra Dimmer.lnk")
)

foreach ($LinkPath in $Shortcuts) {
    $Sc = $WshShell.CreateShortcut($LinkPath)
    $Sc.TargetPath = $PythonwPath
    $Sc.Arguments = "`"$AppScript`""
    $Sc.WorkingDirectory = $RepoRoot
    $Sc.Description = "Ultra Dimmer - Sub-Zero Display Brightness Controller"
    if (Test-Path $IconPath) {
        $Sc.IconLocation = "$IconPath,0"
    }
    $Sc.Save()
    Write-Host "[OK] Created shortcut: $LinkPath"
}

Write-Host ""
Write-Host "Installation complete!"
Write-Host "Ultra Dimmer runs only when you launch it (not added to Windows Startup)."
