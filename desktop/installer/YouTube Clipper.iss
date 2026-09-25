[Setup]
AppId=KadrYouTubeClipper
AppName=YouTube Clipper
AppVersion=1.1.6
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultDirName={localappdata}\Programs\YouTube Clipper
DefaultGroupName=YouTube Clipper
UsePreviousGroup=no
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=YouTube-Clipper-Setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=YouTube Clipper
UninstallDisplayIcon={app}\YouTube Clipper.ico
SetupIconFile=YouTube Clipper.ico

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Files]
Source: "..\dist\YouTube Clipper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "YouTube Clipper.ico"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: files; Name: "{app}\Kadr.exe"
Type: files; Name: "{app}\_internal\tools\ffprobe.exe"
Type: files; Name: "{userprograms}\Kadr\Kadr.lnk"
Type: files; Name: "{userdesktop}\Kadr.lnk"

[Icons]
Name: "{group}\YouTube Clipper"; Filename: "{app}\YouTube Clipper.exe"; IconFilename: "{app}\YouTube Clipper.ico"
Name: "{autodesktop}\YouTube Clipper"; Filename: "{app}\YouTube Clipper.exe"; IconFilename: "{app}\YouTube Clipper.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Skróty:"

[Run]
Filename: "{app}\YouTube Clipper.exe"; Description: "Uruchom YouTube Clipper"; Flags: nowait postinstall skipifsilent
