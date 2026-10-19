; Installateur Windows : ISCC /DVersion=1.0.0 packaging\windows\novapanel.iss
#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
AppId={{6F1C2B9E-4D7A-4E31-9A55-2C8E0B7F3A10}
AppName=NovaPanel
AppVersion={#Version}
AppPublisher=Thibaut Genet
AppPublisherURL=https://github.com/thibautgnt/NovaPanel
AppSupportURL=https://github.com/thibautgnt/NovaPanel/issues
DefaultDirName={autopf}\NovaPanel
DefaultGroupName=NovaPanel
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist
OutputBaseFilename=NovaPanel-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\NovaPanel.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\NovaPanel\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NovaPanel"; Filename: "{app}\NovaPanel.exe"
Name: "{autodesktop}\NovaPanel"; Filename: "{app}\NovaPanel.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NovaPanel.exe"; Description: "{cm:LaunchProgram,NovaPanel}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/IM NovaPanel.exe /F"; Flags: runhidden; RunOnceId: "StopNovaPanel"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "NovaPanel"; Flags: uninsdeletevalue
