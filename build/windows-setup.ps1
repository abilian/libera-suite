<#
.SYNOPSIS
    Everything a Windows machine needs to build the Libera Suite payload and
    run this repository's tests. Idempotent: run it again to check or repair.

.DESCRIPTION
    Run once, as Administrator, from an elevated PowerShell:

        powershell -ExecutionPolicy Bypass -File build\windows-setup.ps1

    Then open a NEW Git Bash (it reads PATH at start) and:

        cd <repo>
        sh build/build.sh fetch && sh build/build.sh configure && sh build/build.sh build
        sh build/payload.sh && sh build/smoke.sh
        sh build/dist.sh && sh build/windows-app.sh      # the installer

    No environment variables to set afterwards: build/common.sh puts
    Strawberry's perl ahead of Git Bash's and defaults BUILD_ROOT to C:/b.

    Every step is checked on the file the build actually uses, not on the
    installer's exit code. SDK 10.0.19041 in particular installs cleanly and
    can still lack user32.lib or cdb.exe, which V8 finds out an hour later.
    notes/14-windows.md has the reasons for each piece.

.PARAMETER SkipVisualStudio
    Do not install Visual Studio Build Tools (use an existing Visual Studio
    that already has the C++ workload).
#>
[CmdletBinding()]
param(
    [switch]$SkipVisualStudio
)

$ErrorActionPreference = 'Stop'
$failures = New-Object System.Collections.Generic.List[string]

function Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }
function Ok($text) { Write-Host "    ok    $text" -ForegroundColor Green }
function Fail($text) {
    Write-Host "    FAIL  $text" -ForegroundColor Red
    $failures.Add($text)
}

# --- preconditions -----------------------------------------------------------

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Run this from an elevated PowerShell (Run as Administrator):' -ForegroundColor Red
    Write-Host '  the SDK, Build Tools and machine-wide PATH all need it.'
    exit 1
}
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host 'winget is missing. Install "App Installer" from the Microsoft Store,' -ForegroundColor Red
    Write-Host 'or on Windows Server: https://learn.microsoft.com/windows/package-manager/winget/'
    exit 1
}

# A PATH read fresh from the registry, so that tools installed a moment ago
# are visible to the checks below without opening a new shell.
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Winget-Install($id, [string]$override = '') {
    $wargs = @('install', '--exact', '--id', $id, '--silent',
              '--accept-package-agreements', '--accept-source-agreements',
              '--disable-interactivity')
    if ($override) { $wargs += @('--override', $override) }
    & winget @wargs | Out-Host
    # winget's own exit codes include "already installed" and "no upgrade
    # available" as failures; the caller checks the file it cares about.
    Refresh-Path
}

# --- command-line tools --------------------------------------------------------

# id, a file that proves it is there, and what needs it.
$tools = @(
    @{ id = 'Git.Git';                       file = 'C:\Program Files\Git\bin\bash.exe';           why = 'Git Bash runs every build script' },
    @{ id = 'Kitware.CMake';                 file = 'C:\Program Files\CMake\bin\cmake.exe';        why = 'core is a CMake build' },
    @{ id = 'Ninja-build.Ninja';             cmd  = 'ninja';                                       why = 'the generator build.sh configures' },
    @{ id = 'Python.Python.3.12';            file = 'C:\Program Files\Python312\python.exe';       why = 'the third-party builders and V8 tooling' },
    @{ id = 'StrawberryPerl.StrawberryPerl'; file = 'C:\Strawberry\perl\bin\perl.exe';             why = 'OpenSSL and ICU tooling; Git''s perl is trimmed' },
    @{ id = 'OpenJS.NodeJS.LTS';             file = 'C:\Program Files\nodejs\node.exe';            why = 'the sdkjs and web-apps pipelines' },
    @{ id = 'NASM.NASM';                     file = 'C:\Program Files\NASM\nasm.exe';              why = 'OpenSSL assembly' },
    @{ id = 'astral-sh.uv';                  cmd  = 'uv';                                          why = 'the repository''s tests and lint' },
    # winget installs Inno Setup under the user's own Programs when it can, so
    # either place will do; build/windows-app.sh looks in both.
    @{ id = 'JRSoftware.InnoSetup';          files = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"); why = 'the installer build/windows-app.sh makes' }
)

function Tool-Present($t) {
    if ($t.files) { return [bool]($t.files | Where-Object { Test-Path $_ } | Select-Object -First 1) }
    if ($t.file) { return Test-Path $t.file }
    return [bool](Get-Command $t.cmd -ErrorAction SilentlyContinue)
}

Step 'command-line tools'
Refresh-Path
foreach ($t in $tools) {
    $present = Tool-Present $t
    if (-not $present) {
        Write-Host "    installing $($t.id) ($($t.why))"
        Winget-Install $t.id ''
        $present = Tool-Present $t
    }
    $proof = if ($t.files) { $t.files -join ' or ' } elseif ($t.file) { $t.file } else { $t.cmd }
    if ($present) { Ok $t.id } else { Fail "$($t.id): installed, but $proof is not there" }
}

# NASM installs without touching PATH. Strawberry happens to carry a nasm too,
# but the build should not depend on which of two installs wins.
$nasmDir = 'C:\Program Files\NASM'
$machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
if ((Test-Path "$nasmDir\nasm.exe") -and ($machinePath -split ';' -notcontains $nasmDir)) {
    [Environment]::SetEnvironmentVariable('Path', "$machinePath;$nasmDir", 'Machine')
    Refresh-Path
    Ok "added $nasmDir to the machine PATH"
}

# --- Visual Studio Build Tools -----------------------------------------------

Step 'Visual Studio with the C++ toolset'
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
function Find-VC {
    if (-not (Test-Path $vswhere)) { return $null }
    & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
}
$vs = Find-VC
if (-not $vs -and -not $SkipVisualStudio) {
    Write-Host '    installing Visual Studio 2022 Build Tools with the C++ workload (long)'
    Winget-Install 'Microsoft.VisualStudio.2022.BuildTools' `
        '--quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended'
    $vs = Find-VC
}
if ($vs) { Ok "C++ toolset in $vs" } else { Fail 'no Visual Studio with Microsoft.VisualStudio.Component.VC.Tools.x86.x64' }

# --- Windows SDK 10.0.19041 with the Debugging Tools -------------------------

# V8 8.9 pins this SDK in its own vcvarsall call, and gn wants cdb.exe, which
# is an optional SDK feature that is off by default. `/features +` asks for
# every feature, so one install brings both.
Step 'Windows SDK 10.0.19041 and its Debugging Tools'
$kits = "${env:ProgramFiles(x86)}\Windows Kits\10"
$user32 = "$kits\Lib\10.0.19041.0\um\x64\user32.lib"
$cdb = "$kits\Debuggers\x64\cdb.exe"
if (-not ((Test-Path $user32) -and (Test-Path $cdb))) {
    Write-Host '    installing Microsoft.WindowsSDK.10.0.19041, every feature'
    Winget-Install 'Microsoft.WindowsSDK.10.0.19041' '/features + /quiet /norestart /ceip off'
}
if (Test-Path $user32) { Ok 'SDK 10.0.19041 (um\x64\user32.lib)' } else { Fail "SDK 10.0.19041 has no $user32" }
if (Test-Path $cdb) { Ok 'Debugging Tools (cdb.exe)' } else {
    Fail "no $cdb -- Settings > Apps > Windows Software Development Kit > Modify > tick Debugging Tools for Windows"
}

# --- Cygwin, for ICU ---------------------------------------------------------

# Upstream builds ICU as Cygwin/MSVC: Cygwin supplies the shell and make, MSVC
# is still the compiler. make and python3 are not in Cygwin's base install and
# neither absence shows until ICU's configure is already running. Its setup
# adds packages to an existing install, so this also repairs a partial one.
Step 'Cygwin with make and python3 (ICU)'
$cygRoot = 'C:\cygwin64'
$cygSetup = "$cygRoot\setup-x86_64.exe"
function Cyg-Has($tool) {
    if (-not (Test-Path "$cygRoot\bin\bash.exe")) { return $false }
    & "$cygRoot\bin\bash.exe" -lc "command -v $tool" *> $null
    return $LASTEXITCODE -eq 0
}
if (-not ((Cyg-Has 'make') -and (Cyg-Has 'python3'))) {
    New-Item -ItemType Directory -Force $cygRoot | Out-Null
    if (-not (Test-Path $cygSetup)) {
        Invoke-WebRequest -UseBasicParsing 'https://cygwin.com/setup-x86_64.exe' -OutFile $cygSetup
    }
    Write-Host '    running Cygwin setup'
    Start-Process -FilePath $cygSetup -Wait -NoNewWindow -ArgumentList @(
        '--quiet-mode', '--no-shortcuts', '--no-startmenu', '--no-desktop',
        '--root', $cygRoot, '--local-package-dir', "$cygRoot\packages",
        '--site', 'http://mirrors.kernel.org/sourceware/cygwin/',
        '--packages', 'make,python3')
}
foreach ($tool in 'make', 'python3') {
    if (Cyg-Has $tool) { Ok "Cygwin $tool" } else { Fail "Cygwin at $cygRoot has no $tool" }
}

# --- long paths --------------------------------------------------------------

# V8's checkout nests deep. build.sh sets core.longpaths in each clone; this is
# the same allowance for everything else that walks the tree.
Step 'long paths'
$fs = 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem'
if ((Get-ItemProperty $fs -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled -ne 1) {
    Set-ItemProperty $fs -Name LongPathsEnabled -Value 1 -Type DWord
}
Ok 'LongPathsEnabled = 1'

# --- git identity ------------------------------------------------------------

# The patch queue is applied with `git am`, which makes commits.
Step 'git identity'
$gitExe = 'C:\Program Files\Git\cmd\git.exe'
if (Test-Path $gitExe) {
    $name = & $gitExe config --global user.name
    $mail = & $gitExe config --global user.email
    if ($name -and $mail) { Ok "$name <$mail>" } else {
        Fail 'git has no user.name/user.email: git config --global user.name "..." ; git config --global user.email ...'
    }
}

# --- the build's own check ---------------------------------------------------

# The same question the build asks, in a clean Git Bash, so a pass here means
# `sh build/build.sh configure` will get past its first line.
Step 'build/toolchain.sh check, in a fresh Git Bash'
$repo = Split-Path -Parent $PSScriptRoot
$bash = 'C:\Program Files\Git\bin\bash.exe'
if (Test-Path $bash) {
    # Git Bash rebuilds PATH from ORIGINAL_PATH when it finds one; a shell
    # started from this one would otherwise see the PATH from before installs.
    foreach ($v in 'ORIGINAL_PATH', 'MSYSTEM', 'EXEPATH') { Remove-Item "Env:$v" -ErrorAction SilentlyContinue }
    $repoUnix = (& $bash -lc "cygpath -u '$repo'").Trim()
    & $bash -lc "cd '$repoUnix' && sh build/toolchain.sh check"
    if ($LASTEXITCODE -eq 0) { Ok 'toolchain ok' } else { Fail 'build/toolchain.sh check failed (above)' }
}

Write-Host ''
if ($failures.Count -eq 0) {
    Write-Host 'Ready. Open a NEW Git Bash and run, from the repository:' -ForegroundColor Green
    Write-Host '    sh build/build.sh fetch && sh build/build.sh configure && sh build/build.sh build'
    Write-Host '    sh build/payload.sh && sh build/smoke.sh'
    Write-Host '    sh build/dist.sh && sh build/windows-app.sh    # the installer'
    exit 0
}
Write-Host "Not ready: $($failures.Count) problem(s)." -ForegroundColor Red
$failures | ForEach-Object { Write-Host "  - $_" }
exit 1
