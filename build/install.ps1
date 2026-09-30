# Libera Suite for Windows: download the installer from the origin and run it.
#
#   irm https://cdn.abilian.com/libera/install.ps1 | iex
#
# The Windows sibling of install.sh, and the same contract: nothing outside the
# user's own profile, no administrator rights, idempotent (run it again to
# upgrade or repair), and every step checked by what it produced rather than
# by an exit status.
#
# What it does: reads bundles/latest for the current version, downloads
# bundles/Libera-Suite-Setup-<version>.exe and its .sha256, checks the hash,
# runs the installer silently, and then checks that Libera Suite is installed
# and runs. The installer is the same file a user can download and
# double-click; this only saves the clicks.
#
# `irm | iex` passes no arguments, so the options are environment variables:
#
#   $env:LIBERA_ORIGIN       where to download from (default: the public CDN)
#   $env:LIBERA_VERSION      a version other than the latest
#   $env:LIBERA_NO_DESKTOP   set to 1 for no desktop icon
#
# Written for Windows PowerShell 5.1, which every Windows 10 and 11 has; it
# runs unchanged under PowerShell 7.

function Install-LiberaSuite {
    [CmdletBinding()]
    param()

    $ErrorActionPreference = 'Stop'
    # Invoke-WebRequest's progress bar makes a 100 MB download many times
    # slower in Windows PowerShell 5.1, and there is a line per step anyway.
    $ProgressPreference = 'SilentlyContinue'
    # Windows PowerShell 5.1 still offers TLS 1.0 first, which the CDN refuses.
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $origin = if ($env:LIBERA_ORIGIN) { $env:LIBERA_ORIGIN.TrimEnd('/') } else { 'https://cdn.abilian.com/libera' }

    function Say($text) { Write-Host "==> $text" -ForegroundColor Cyan }

    # --- this machine -------------------------------------------------------------
    if ([Environment]::OSVersion.Version.Major -lt 10) {
        throw 'Libera Suite needs Windows 10 or later.'
    }
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw 'Libera Suite needs 64-bit Windows.'
    }
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
        # x64 programs run on Windows on ARM through emulation, and so does
        # Libera Suite; there is no native build yet. Said, not refused.
        Write-Host '    Windows on ARM: the x64 build runs under emulation.' -ForegroundColor Yellow
    }

    # --- which version ------------------------------------------------------------
    $version = $env:LIBERA_VERSION
    if (-not $version) {
        # One line holding the version, as install.sh reads it. Checked for
        # shape: a portal page or an error body answered with 200 is not one.
        $version = (Invoke-RestMethod -Uri "$origin/bundles/latest" -UseBasicParsing).ToString().Trim()
    }
    if ($version -notmatch '^[0-9]+(\.[0-9]+)*$') {
        throw "$origin/bundles/latest does not hold a version number: '$version'"
    }

    $name = "Libera-Suite-Setup-$version.exe"
    $url = "$origin/bundles/$name"
    $work = Join-Path ([IO.Path]::GetTempPath()) "libera-install-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
    New-Item -ItemType Directory -Force $work | Out-Null
    $setup = Join-Path $work $name

    try {
        # --- download and check -----------------------------------------------
        Say "Libera Suite $version, from $origin"
        try {
            $expected = (Invoke-RestMethod -Uri "$url.sha256" -UseBasicParsing).ToString().Trim().Split(' ')[0].ToLower()
        } catch {
            throw "There is no Windows build of Libera Suite $version at $origin ($url.sha256)."
        }
        if ($expected -notmatch '^[0-9a-f]{64}$') {
            throw "$url.sha256 does not hold a SHA-256: '$expected'"
        }

        Say "downloading $name"
        Invoke-WebRequest -Uri $url -OutFile $setup -UseBasicParsing
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup).Hash.ToLower()
        if ($actual -ne $expected) {
            throw "$name does not match its published SHA-256 (expected $expected, got $actual). Nothing was installed."
        }
        Write-Host "    SHA-256 matches ($([math]::Round((Get-Item -LiteralPath $setup).Length / 1MB)) MB)"

        # --- install ----------------------------------------------------------
        # Silent, but not invisible: /SILENT would show a progress window;
        # /VERYSILENT shows nothing, and this script says what is happening.
        Say 'installing (about a minute: the editors and fonts are set up for this machine)'
        $tasks = if ($env:LIBERA_NO_DESKTOP -eq '1') { '' } else { 'desktopicon' }
        $log = Join-Path $work 'setup.log'
        $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/TASKS=$tasks", "/LOG=`"$log`"")
        $process = Start-Process -FilePath $setup -ArgumentList $arguments -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "The installer stopped with code $($process.ExitCode). Its log: $log"
        }

        # --- check what it produced -------------------------------------------
        $app = Join-Path $env:LOCALAPPDATA 'Programs\Libera Suite'
        $cli = Join-Path $app 'libera-cli.exe'
        if (-not (Test-Path -LiteralPath (Join-Path $app 'Libera.exe'))) {
            throw "The installer finished, but there is no Libera.exe in $app. Its log: $log"
        }
        $reported = & $cli -V 2>&1 | Out-String
        if ($reported -notmatch 'libera') {
            throw "Libera Suite is installed but does not run: $reported"
        }
        $status = & $cli --payload-status 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "Libera Suite is installed but its editors are not: $status"
        }

        Say "installed: $($reported.Trim())"
        Write-Host '    Open it from the Start menu or the desktop, or double-click a document.'
        Write-Host '    Remove it from Settings > Apps > Installed apps, like any other.'
    } catch {
        Write-Host ''
        Write-Host "Libera Suite was not installed: $($_.Exception.Message)" -ForegroundColor Red
        # Kept for the report, since it is the evidence.
        Write-Host "    (downloads and logs kept in $work)"
        throw
    }
    # Only on success; a failure keeps the evidence.
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}

Install-LiberaSuite
