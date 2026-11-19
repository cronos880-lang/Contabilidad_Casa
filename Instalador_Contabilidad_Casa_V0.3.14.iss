; Instalador completo Windows V0.3.14; mismo AppId y rutas que V0.3.9
#define AppName "Contabilidad Casa"
#define AppVersion "0.3.14"
[Setup]
AppId={{91D877A0-0DD7-431D-A420-74B111C944B4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} V{#AppVersion}
AppPublisher=Contabilidad Casa
DefaultDirName={localappdata}\Programs\Contabilidad Casa
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
UsePreviousAppDir=yes
WizardStyle=modern
MinVersion=10.0
DisableProgramGroupPage=yes
SetupIconFile=Contabilidad_Casa.ico
UninstallDisplayIcon={app}\ContabilidadCasa.exe
OutputDir=Salida
OutputBaseFilename=Instalar_Contabilidad_Casa_V0.3.14
Compression=lzma2
SolidCompression=yes
Uninstallable=yes
DisableDirPage=no
CloseApplications=yes
RestartApplications=no
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce
[Files]
Source: "dist\ContabilidadCasa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Contabilidad Casa"; Filename: "{app}\ContabilidadCasa.exe"; WorkingDir: "{app}"; Comment: "Contabilidad Casa V0.3.14"
Name: "{autoprograms}\Desinstalar Contabilidad Casa"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Contabilidad Casa"; Filename: "{app}\ContabilidadCasa.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\ContabilidadCasa.exe"; Description: "Abrir Contabilidad Casa V0.3.14"; Flags: nowait postinstall skipifsilent
; NO ejecutar borrados sobre %LOCALAPPDATA%\ContabilidadCasaV031, perfil, Excel ni copias.
