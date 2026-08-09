<#
.SYNOPSIS
    Run Stash.exe --selftest and turn its exit code into a pass or a failure.

.DESCRIPTION
    Stash.exe is built --windowed, i.e. a GUI-subsystem binary. Both cmd and
    pwsh return the moment they launch one, so $LASTEXITCODE is meaningless
    here and the exit code has to be collected from a Process object.

    The timeout is not optional. A --windowed PyInstaller build renders an
    unhandled exception as a modal message box; on an unattended machine that
    is an infinite wait, so without a deadline a broken build hangs the job
    until the six-hour ceiling instead of failing in seconds.

    Requires PowerShell 7 for Kill($true), so run it with pwsh, never the
    Windows PowerShell 5.1 that `shell: powershell` selects.

.EXAMPLE
    pwsh scripts\ci\selftest.ps1 -Exe build\dist\Stash\Stash.exe -Label 'unpacked build'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $Exe,
    [string] $Label = '',
    [int]    $TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
if (-not $Label) { $Label = $Exe }

if (-not (Test-Path -LiteralPath $Exe)) { throw "$Label — not found: $Exe" }

$log = Join-Path ([System.IO.Path]::GetTempPath()) ("stash-selftest-{0}.log" -f [guid]::NewGuid().ToString('N'))

Write-Host "::group::selftest — $Label"
Write-Host "exe: $Exe"

$proc = Start-Process -FilePath $Exe -PassThru `
        -ArgumentList '--selftest', '--selftest-log', $log

if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    try { $proc.Kill($true) } catch { }
    Write-Host '::endgroup::'
    throw "$Label — no exit within ${TimeoutSeconds}s. A windowed build shows a modal error dialog instead of crashing, so this usually means an unhandled exception before the selftest ran."
}
$proc.WaitForExit()          # settles the exit code after the timed wait
$code = $proc.ExitCode

if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log | Write-Host }
else { Write-Host "(the selftest wrote no log to $log)" }
Write-Host '::endgroup::'

if ($code -ne 0) { throw "$Label — selftest failed, exit code $code" }
Write-Host "$Label — selftest passed"
