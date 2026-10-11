; GitClean Archiver kurulum sihirbazı (Inno Setup 6).
; Derleme: python build_installer.py   (EXE'yi derler, sürümü src/version.py'den alıp bu betiği ISCC ile çalıştırır)
; Elle:    ISCC /DAppVersion=2.1.0 packaging\GitCleanArchiver.iss   (önce dist\GitCleanArchiver.exe derlenmiş olmalı)

#ifndef AppVersion
  #error AppVersion tanımlı değil: ISCC /DAppVersion=X.Y.Z ile ya da build_installer.py ile derleyin.
#endif

#define AppName "GitClean Archiver"
#define AppExe "GitCleanArchiver.exe"
#define RepoUrl "https://github.com/Yusufygc/Clean_Zipper"

[Setup]
; AppId sabittir: sonraki sürümler aynı kurulumun üstüne yazılır (güncelleme); ASLA değiştirmeyin.
AppId={{B4C7E1A2-5D3F-4E8A-9C21-6F0A7D9E3B58}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
AppPublisherURL={#RepoUrl}
AppSupportURL={#RepoUrl}/issues
AppUpdatesURL={#RepoUrl}/releases
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup

; Yönetici hakkı gerekmez: varsayılan kullanıcıya özel kurulum (%LOCALAPPDATA%\Programs), sihirbaz "tüm kullanıcılar" seçeneği sunar.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; Çalışan uygulama kurulum sırasında kapatılır (güncellemede dosya kilidi olmasın); kurulumdan sonra yeniden başlatılmaz.
CloseApplications=yes
RestartApplications=no

OutputDir=..\dist\installer
OutputBaseFilename=GitCleanArchiver-Setup-{#AppVersion}
SetupIconFile=..\resources\icons\app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=wizard_large.bmp
WizardSmallImageFile=wizard_small.bmp
Compression=lzma2/ultra64
SolidCompression=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; AppUserModelID uygulamadaki değerle aynıdır (src/qml_ui/app.py): görev çubuğu sabitlemesi kısayolla eşleşir.
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "gitclean.archiver.qml"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; AppUserModelID: "gitclean.archiver.qml"

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; Kullanıcı ayarları (~\.gitclean) ve proje yedekleri kaldırıcı tarafından SİLİNMEZ: kullanıcı verisidir.
