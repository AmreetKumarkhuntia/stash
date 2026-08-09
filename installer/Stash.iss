; Inno Setup script for the Stash panel.
;
; Build it with:  python.exe scripts/build_installer.py
; which produces the PyInstaller app first and then compiles this.
;
; Installs per-user into %LOCALAPPDATA%\Programs, so there is no UAC prompt and
; no admin account needed — the panel writes only to the user profile anyway.

#define AppName        "Stash"
#define AppShortName   "Stash"
#define AppPublisher   "Amreet Khuntia"
#define AppExe         "Stash.exe"
#define AppUrl         "https://github.com/AmreetKumarkhuntia/stash"
#define AppComments    "Searchable media library that drags into DaVinci Resolve"

; Passed in by build_installer.py: /DAppVersion=... /DSourceDir=... /DOutputDir=...
;
; The version below is only a fallback for compiling this script by hand. The
; real one comes from stashlib/_version.py, the single place it lives. If the
; fallback ever shipped it would silently mislabel a release, so CI checks the
; produced filename and the DisplayVersion the installer writes.
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\..\dist\Stash"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

[Setup]
; New GUID for the rename: a different product identity, so the old
; "Meme & SFX Library" entry is never silently upgraded or replaced by this one.
AppId={{2F8B71C4-9E5A-4D63-B0A8-6C4E17D95B32}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
; These four land in the uninstall registry key as Comments, URLInfoAbout,
; HelpLink and URLUpdateInfo, which is what Settings > Apps > Installed apps
; reads. Without them the entry is a bare name with no way back to the project,
; and no route to a newer build for someone who did not install it themselves.
AppComments={#AppComments}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases/latest
DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
OutputDir={#OutputDir}
OutputBaseFilename={#AppShortName}-Setup-{#AppVersion}
SetupIconFile=..\panel\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user install: no admin rights, installs under %LOCALAPPDATA%\Programs.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
DisableDirPage=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Inert unless build_installer.py --sign-command is used, which passes
; /DSign and /Sstashsign=<command>. Absent signing credentials mean an
; unsigned build, not a failed one — CI has no certificate today.
#ifdef Sign
SignTool=stashsign
SignedUninstaller=yes
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; PyInstaller and Qt drop caches next to the app; leave nothing behind.
Type: filesandordirs; Name: "{app}"

[Code]
// The library index and thumbnail cache live outside {app}, in the user
// profile, and can represent a long scan. Rebuilding them is cheap (~10 s) but
// favourites and hand-written tags are not recoverable — so ask rather than
// assume, and default to keeping them.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // A silent uninstall must never destroy user data. /SUPPRESSMSGBOXES
    // answers this prompt with Yes regardless of MB_DEFBUTTON2, so asking at
    // all in silent mode would delete favourites and tags unattended.
    if UninstallSilent() then
      Exit;

    DataDir := ExpandConstant('{localappdata}\Stash\library');
    if DirExists(DataDir) then
    begin
      if MsgBox('Also delete your library index, thumbnails, favourites and tags?'
                + #13#10 + #13#10
                + DataDir + #13#10 + #13#10
                + 'Choose No to keep them for a future reinstall.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
