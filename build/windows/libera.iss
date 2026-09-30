; Libera Suite for Windows: the installer.
;
; Built by build/windows-app.sh, which passes:
;   /DAppVersion=0.2.2   /DAppDir=<frozen app>   /DPayloadDir=<dist artifacts>
;   /DIconFile=<.ico>    /DAssociations=<generated .iss>  /DOutputDir=<dir>
;
; Per-user and without administrator rights: the application goes to
; %LOCALAPPDATA%\Programs\Libera Suite, its file types to HKCU, and nothing
; asks for elevation unless the machine lacks the WebView2 runtime, which is
; Microsoft's installer and asks for itself.
;
; The editors themselves (the payload) are installed at the end by the
; application's own `--payload-install`, from artifacts carried in the setup:
; the same verified path every other channel uses, checked against the
; manifest built into the application. See notes/14-windows.md.

#define AppName "Libera Suite"
#define AppExe "Libera.exe"
#define AppId "eu.liberasuite.Libera"

[Setup]
AppId={{7B0C6E3A-4F59-4E0B-9C51-4A1F9E2B7D11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Abilian
AppPublisherURL=https://liberasuite.eu/
AppSupportURL=https://docs.liberasuite.eu/
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
ChangesAssociations=yes
; A running Libera Suite holds its DLLs open; the Restart Manager asks it to
; close rather than failing on a locked file halfway through.
CloseApplications=yes
RestartApplications=no
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
OutputDir={#OutputDir}
OutputBaseFilename=Libera-Suite-Setup-{#AppVersion}
; The payload artifacts are gzip already; lzma2 over them gains little and
; costs minutes, so compress the application and store the rest nearly as is.
Compression=lzma2/fast
SolidCompression=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Put a Libera Suite icon on the desktop"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\*"; DestDir: "{app}\payload-dist"; Flags: ignoreversion

[InstallDelete]
; An older version's frozen tree, so modules it had and this one dropped do
; not linger and get imported.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppId}"; Comment: "Documents, spreadsheets and presentations"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppId}"; Tasks: desktopicon

; Generated from src/libera/host/apps.py by build/windows/associations.py.
#include Associations

[Run]
Filename: "{app}\{#AppExe}"; Description: "Open {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The editors installed by the payload step. Documents, the Recent list and
; unsaved sessions stay: they are the user's, and a reinstall finds them.
Type: filesandordirs; Name: "{localappdata}\Libera Suite\payload"
Type: files; Name: "{localappdata}\Libera Suite\instance.json"

[Code]
const
  WebView2Key = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2Bootstrapper = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703';

{ The runtime pywebview draws the editor with. Windows 10 and 11 carry it;
  a stripped-down machine may not, and without it Libera.exe opens nothing. }
function HasWebView2(): Boolean;
var
  Version: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\' + WebView2Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

procedure InstallWebView2();
var
  ResultCode: Integer;
begin
  WizardForm.StatusLabel.Caption := 'Installing the Microsoft Edge WebView2 runtime...';
  try
    DownloadTemporaryFile(WebView2Bootstrapper, 'MicrosoftEdgeWebview2Setup.exe', '', nil);
    Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '',
         SW_SHOW, ewWaitUntilTerminated, ResultCode);
  except
    Log('WebView2 download failed: ' + GetExceptionMessage);
  end;
  if not HasWebView2() then
    MsgBox('Libera Suite needs the Microsoft Edge WebView2 runtime, and it could not be installed.' + #13#10#13#10 +
           'Install it from https://developer.microsoft.com/microsoft-edge/webview2/ and open Libera Suite again.',
           mbError, MB_OK);
end;

{ The editors, from the artifacts carried in this setup, through the
  application's own installer: it checks every artifact against the manifest
  built into the application, unpacks them, and generates the font index for
  this machine's paths. Run through cmd so its report can be kept. }
procedure InstallPayload();
var
  ResultCode: Integer;
  LogFile, Report: String;
  Lines: TArrayOfString;
  I: Integer;
begin
  WizardForm.StatusLabel.Caption := 'Installing the editors and fonts...';
  LogFile := ExpandConstant('{localappdata}\Libera Suite\install.log');
  ForceDirectories(ExtractFileDir(LogFile));
  if Exec(ExpandConstant('{cmd}'),
          '/c ""' + ExpandConstant('{app}\libera-cli.exe') + '" --payload-install --from "' +
          ExpandConstant('{app}\payload-dist') + '" > "' + LogFile + '" 2>&1"',
          '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
  begin
    { Installed into %LOCALAPPDATA%\Libera Suite\payload; the artifacts are
      spent, and they are most of the setup's size. }
    DelTree(ExpandConstant('{app}\payload-dist'), True, True, True);
    Exit;
  end;
  Report := '';
  if LoadStringsFromFile(LogFile, Lines) then
    for I := 0 to GetArrayLength(Lines) - 1 do
      if I >= GetArrayLength(Lines) - 12 then
        Report := Report + Lines[I] + #13#10;
  MsgBox('The editors could not be installed (exit ' + IntToStr(ResultCode) + ').' + #13#10#13#10 +
         Report + #13#10 + 'The full report is in ' + LogFile, mbError, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not HasWebView2() then
      InstallWebView2();
    InstallPayload();
  end;
end;
