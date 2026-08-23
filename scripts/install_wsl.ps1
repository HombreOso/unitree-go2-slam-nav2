<#
  Stage 1a - Install WSL2 + Ubuntu 22.04 on Windows.

  MUST be run from an ELEVATED PowerShell (Run as Administrator).
  A reboot is required after this completes.

  After the reboot, run:  scripts\setup_ros2.ps1
#>

$ErrorActionPreference = 'Stop'
$log = Join-Path $PSScriptRoot '..\results\stage1_wsl_install.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

function Log($m) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator. Right-click PowerShell -> Run as Administrator."
    exit 1
}

Log "Enabling Windows optional features (WSL + VirtualMachinePlatform)."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Log "Installing WSL2 with Ubuntu 22.04 (ROS 2 Humble target distro)."
# --no-launch keeps this non-interactive; the distro is initialised by setup_ros2.ps1 later.
wsl.exe --install -d Ubuntu-22.04 --no-launch
wsl.exe --set-default-version 2

Log "Updating the WSL kernel."
wsl.exe --update

Log "DONE. A REBOOT IS REQUIRED before WSL can be used."
Log "After rebooting, run:  powershell -ExecutionPolicy Bypass -File scripts\setup_ros2.ps1"
