; Inno Setup script for the IMS Windows installer.
; Build with:  ISCC.exe /DAppVersion=1.0.0 installer.iss
; (expects packaging\dist\ims\ from PyInstaller — see build.ps1)
;
; The database lives in {localappdata}\IMS\pgdata, OUTSIDE the install dir:
; installs, upgrades and uninstalls never touch it, so data always persists.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{9C2C41C7-6E1B-4E52-9B44-1D8A55C5A1B0}
AppName=IMS
AppVersion={#AppVersion}
AppVerName=IMS {#AppVersion}
AppPublisher=Glascutr
DefaultDirName={autopf}\IMS
DefaultGroupName=IMS
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=ims-setup-{#AppVersion}-windows-x64
SetupIconFile=..\icons\ims.ico
UninstallDisplayIcon={app}\ims.exe
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
WizardStyle=modern

[Files]
Source: "..\dist\ims\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\IMS"; Filename: "{app}\ims.exe"
Name: "{autodesktop}\IMS"; Filename: "{app}\ims.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
Filename: "{app}\ims.exe"; Description: "{cm:LaunchProgram,IMS}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Only the installed program is removed. {localappdata}\IMS (database, product
; images) is intentionally left behind so a reinstall finds all data again.
Type: filesandordirs; Name: "{app}"

[Code]
procedure StopDatabase(PgCtl: String);
var
  DataDir: String;
  ResultCode: Integer;
begin
  DataDir := ExpandConstant('{localappdata}\IMS\pgdata');
  if FileExists(PgCtl) and DirExists(DataDir) then
    Exec(PgCtl, 'stop -D "' + DataDir + '" -m fast -w -t 30', '',
         SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  { Stop a running embedded server so its files in {app} can be replaced. }
  StopDatabase(ExpandConstant('{app}\_internal\pgsql\bin\pg_ctl.exe'));
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    StopDatabase(ExpandConstant('{app}\_internal\pgsql\bin\pg_ctl.exe'));
end;
