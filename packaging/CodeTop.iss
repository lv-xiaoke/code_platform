#ifndef StageDir
  #error StageDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
[Setup]
AppId={{D5C6526A-3931-4391-983E-F4E14066E390}
AppName=CodeTop Local
AppVersion=1.6.0
AppPublisher=CodeTop Local
DefaultDirName={localappdata}\Programs\CodeTopLocal
DefaultGroupName=CodeTop Local
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=CodeTop-Setup-1.6.0-windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
UninstallDisplayIcon={app}\CodeTop.exe
[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"
Name: "startmenu"; Description: "创建开始菜单快捷方式"
[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autodesktop}\CodeTop 刷题"; Filename: "{app}\CodeTop.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autoprograms}\CodeTop 刷题"; Filename: "{app}\CodeTop.exe"; WorkingDir: "{app}"; Tasks: startmenu
[Run]
Filename: "{app}\CodeTop.exe"; Description: "启动 CodeTop 刷题"; Flags: nowait postinstall skipifsilent
