# Open a real window from the *released* Libera Suite on Windows, and prove
# something was drawn. The Windows half of `lb release publish`'s downloads.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File released-gui.ps1 [-Out FILE] [-Doc FILE]
#   ... -Installer Libera-Suite-Setup-X.Y.Z.exe       one not published yet (`stage`)
#
# It installs Libera Suite the way a user does, `irm .../install.ps1 | iex`,
# which replaces this account's own; refuses a --version that is not the one
# bundles/latest-windows names. Given -Installer, it checks that file against
# the .sha256 beside it and runs it as install.ps1 runs the one it downloads,
# and the version is the one in its name. Then it converts a document to docx and back to text
# and looks for its words; then opens the document in a window and counts the
# colours of a screenshot, as released-gui.sh does under Xvfb.
#
# ssh runs in session 0, which has no desktop, so the window is started by a
# scheduled task with /IT in the session of whoever is logged in, as
# build/windows/gui-test.sh does. A locked screen draws nothing: it is said,
# and is not a pass. The screenshot is taken DPI-aware: at 150% a process that
# is not sees 1280x720 of a 1920x1080 screen, and its picture of a window that
# fits looks like one that does not.
#
# The verdict is the line __LIBERA__=ok or the reason, as in released-gui.sh.
# Written in ASCII on purpose: Windows PowerShell 5.1 reads a script with no
# byte-order mark in the ANSI code page.
param(
    [string]$Out = "$HOME\released-gui.png",
    [string]$Doc = "",
    [string]$Installer = "",
    [string]$Origin = $(if ($env:LIBERA_ORIGIN) { $env:LIBERA_ORIGIN } else { 'https://cdn.abilian.com/libera' })
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Long enough for the converter and the editor's first load on a cold machine,
# then this much more for a mapped window to paint.
$Timeout = 90
$Settle = 10
$MinColours = 24

function Say([string]$m) { Write-Output $m }
function Step([string]$m) { Write-Output ''; Write-Output "==> $m" }
function Die([string]$m) {
    Write-Output ''
    Write-Output "FAIL: $m"
    Write-Output "__LIBERA__=$(($m -split "`n")[0])"
    exit 1
}

$app = Join-Path $env:LOCALAPPDATA 'Programs\Libera Suite'
$cli = Join-Path $app 'libera-cli.exe'
$work = Join-Path $env:TEMP 'libera-released-gui'
New-Item -ItemType Directory -Force $work | Out-Null

# --- install what users get ---------------------------------------------------

if ($Installer) {
    if (-not (Test-Path $Installer)) { Die "no such installer: $Installer" }
    $name = [IO.Path]::GetFileName($Installer)
    if ($name -notmatch '^Libera-Suite-Setup-(.+)\.exe$') { Die "$name is not named Libera-Suite-Setup-VERSION.exe" }
    $want = $Matches[1]
    Step "installing the staged $want"
    if (-not (Test-Path "$Installer.sha256")) { Die "no $name.sha256 beside it" }
    $expected = (Get-Content "$Installer.sha256" -Raw).Trim().Split(' ')[0].ToLower()
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Installer).Hash.ToLower()
    if ($actual -ne $expected) { Die "$name does not match its .sha256" }
    # The arguments install.ps1 gives the one it downloads.
    $log = Join-Path $work 'setup.log'
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TASKS=desktopicon', "/LOG=`"$log`"")
    $process = Start-Process -FilePath $Installer -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) { Die "the installer stopped with code $($process.ExitCode); its log: $log" }
} else {
    try { $want = ([string](Invoke-RestMethod "$Origin/bundles/latest-windows")).Trim() }
    catch { Die "could not read $Origin/bundles/latest-windows" }
    Step "installing the published $want with install.ps1"
    try { Invoke-RestMethod "$Origin/install.ps1" | Invoke-Expression }
    catch { Die "install.ps1 failed: $_" }
}

Step 'what is installed here'
if (-not (Test-Path $cli)) { Die "no $cli after install.ps1" }
$version = (& $cli --version | Out-String).Trim()
Say $version
if (-not $version.StartsWith("libera $want ")) { Die "this is not the published ${want}: $version" }

# --- the converter: words in, the same words out -----------------------------

Step 'the converter'
$words = 'Released check: the quick brown fox jumps over the lazy dog, z' + [char]0xE9 + 'ro accent.'
$md = Join-Path $work 'released-gui.md'
$docx = Join-Path $work 'released-gui.docx'
$txt = Join-Path $work 'released-gui.txt'
Remove-Item $docx, $txt -ErrorAction SilentlyContinue
[IO.File]::WriteAllText($md, "# Released check`n`n$words`n", [Text.UTF8Encoding]::new($false))
& $cli --convert $md -t docx --outdir $work 2>&1 | Out-Null
& $cli --convert $docx -t txt --outdir $work 2>&1 | Out-Null
if (-not (Test-Path $txt)) { Die 'markdown to docx to text made no text file' }
$back = [IO.File]::ReadAllText($txt, [Text.Encoding]::UTF8)
if (-not $back.Contains($words)) { Die "the words did not come back through docx: $back" }
Say '    markdown to docx to text, the words intact'

# --- a real window, in the desktop session ------------------------------------

Step 'a real window, in the desktop session'
if (Get-Process LogonUI -ErrorAction SilentlyContinue) {
    Die 'the screen is locked, so no window can be drawn: unlock it and run this again'
}
if (-not $Doc) { $Doc = $docx }
$title = [IO.Path]::GetFileName($Doc)
$result = Join-Path $work 'window.txt'
$shot = Join-Path $work 'window.png'
Remove-Item $result, $shot -ErrorAction SilentlyContinue

$child = @'
$ErrorActionPreference = 'Stop'
Add-Type -ReferencedAssemblies System.Drawing @"
using System; using System.Collections.Generic; using System.Drawing;
using System.Runtime.InteropServices;
public static class Probe {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect r);
    public static int Colours(string path) {
        using (var b = new Bitmap(path)) {
            var seen = new HashSet<int>();
            for (int y = 0; y < b.Height; y++)
                for (int x = 0; x < b.Width; x++) seen.Add(b.GetPixel(x, y).ToArgb());
            return seen.Count;
        }
    }
}
"@
[Probe]::SetProcessDPIAware() | Out-Null
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$lines = @()
$p = Start-Process -PassThru '@APP@\Libera.exe' -ArgumentList '"@DOC@"'
$w = $null
for ($i = 0; $i -lt @TIMEOUT@ -and -not $w; $i++) {
    Start-Sleep 1
    $w = Get-Process | Where-Object { $_.MainWindowTitle -like '@TITLE@*' } | Select-Object -First 1
}
if (-not $w) { $lines += 'window=none' } else {
    Start-Sleep @SETTLE@
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $b = $screen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    [System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save('@SHOT@')
    $bmp.Dispose()
    $r = New-Object Probe+Rect
    [Probe]::GetWindowRect($w.MainWindowHandle, [ref]$r) | Out-Null
    $a = $screen.WorkingArea
    $lines += "window=$($w.MainWindowTitle)"
    $lines += "rect=$($r.Left),$($r.Top),$($r.Right),$($r.Bottom)"
    $lines += "area=$($a.Left),$($a.Top),$($a.Right),$($a.Bottom)"
    $lines += "size=$($b.Width)x$($b.Height)"
    $lines += "colours=$([Probe]::Colours('@SHOT@'))"
}
Set-Content '@RESULT@' $lines
# Continue: under Stop, Windows PowerShell 5.1 makes a native program's stderr
# a terminating error, and the second taskkill finds its process gone with the
# first one's tree.
$ErrorActionPreference = 'Continue'
taskkill /T /F /PID $p.Id 2>&1 | Out-Null
if ($w) { taskkill /T /F /PID $w.Id 2>&1 | Out-Null }
'@
$child = $child.Replace('@APP@', $app).Replace('@DOC@', $Doc).Replace('@TITLE@', $title)
$child = $child.Replace('@TIMEOUT@', $Timeout).Replace('@SETTLE@', $Settle)
$child = $child.Replace('@SHOT@', $shot).Replace('@RESULT@', $result)
$script = Join-Path $work 'window.ps1'
Set-Content $script $child

$task = 'libera-released-gui'
# \" and not `": Windows PowerShell 5.1 hands a native program its arguments
# without escaping the quotes inside one, and schtasks then cut /tr short and
# made a task that ran nothing.
schtasks /create /tn $task /tr "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \`"$script\`"" /sc once /st 23:59 /it /f | Out-Null
schtasks /run /tn $task | Out-Null
$limit = $Timeout + $Settle + 120
for ($i = 0; $i -lt $limit -and -not (Test-Path $result); $i++) { Start-Sleep 1 }
schtasks /delete /tn $task /f | Out-Null
if (-not (Test-Path $result)) { Die "the window task said nothing after ${limit}s" }

$facts = @{}
foreach ($line in Get-Content $result) { $k, $v = $line -split '=', 2; $facts[$k] = $v }
if ($facts['window'] -eq 'none') { Die "no window titled $title after ${Timeout}s" }
Say "    $($facts['window'])"
Say "    window opened, $($facts['colours']) colours in a $($facts['size']) screenshot"
if ([int]$facts['colours'] -lt $MinColours) {
    Die "only $($facts['colours']) colours: the window opened empty. Look at $Out."
}
# A maximised window reaches a few pixels past the screen with its invisible
# border; one sized past the screen, as before 0.7, reaches much further.
$r = [int[]]($facts['rect'] -split ',')
$a = [int[]]($facts['area'] -split ',')
$slack = 16
if ($r[0] -lt $a[0] - $slack -or $r[1] -lt $a[1] - $slack -or $r[2] -gt $a[2] + $slack -or $r[3] -gt $a[3] + $slack) {
    Die "the window ($($facts['rect'])) does not fit the screen ($($facts['area']))"
}
Copy-Item $shot $Out -Force
Say "    $Out"

Step 'PASS'
Say "    $want, installed as a user installs it, converted a document and drew it in a window."
Say '__LIBERA__=ok'
