; Contabilidad Casa V0.3.9 | instalador Inno Setup 6 por usuario.
; PROGRAMA: carpeta de instalacion | DATOS: perfil de Windows/documentos.
; Sin PowerShell, sin VBS, sin comandos codificados, sin descargas ocultas.
#define AppName "Contabilidad Casa"
#define AppVersion "0.3.9"

[Setup]
; Mismo identificador que el instalador convencional anterior; actualiza sin duplicar.
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
OutputBaseFilename=Instalar_Contabilidad_Casa_V0.3.9
Compression=lzma2
SolidCompression=yes
Uninstallable=yes
DisableDirPage=no
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
; Solo binarios y plantilla generica sin datos. _internal incluye Python empaquetado.
Source: "dist\ContabilidadCasa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Contabilidad Casa"; Filename: "{app}\ContabilidadCasa.exe"; WorkingDir: "{app}"; Comment: "Contabilidad Casa V0.3.9"
Name: "{autoprograms}\Desinstalar Contabilidad Casa"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Contabilidad Casa"; Filename: "{app}\ContabilidadCasa.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\ContabilidadCasa.exe"; Description: "Abrir Contabilidad Casa V0.3.9"; Flags: nowait postinstall skipifsilent

; No se borra ni sobrescribe ningun dato en %LOCALAPPDATA%\ContabilidadCasaV031
; ni las carpetas que el usuario haya elegido para sus contabilidades.
; No se crea ninguna contabilidad predeterminada en una instalacion nueva.
