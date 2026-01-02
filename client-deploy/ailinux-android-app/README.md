# AILinux Android Client

Android-optimierte Version des AILinux Clients mit Kivy/KivyMD.

## Features

- Material Design UI (KivyMD)
- Login mit Email/Password
- Chat mit Model-Auswahl
- Tier-basierte Model-Verfügbarkeit
- Offline-Credential-Storage
- Dark Theme

## Struktur

```
ailinux-android-app/
├── main.py                     # Entry Point
├── buildozer.spec              # Android Build Config
├── requirements.txt            # Python Dependencies
├── ailinux_android/
│   ├── core/
│   │   ├── api_client.py       # HTTP Client
│   │   └── storage.py          # Secure Storage
│   └── screens/
│       ├── login.py            # Login Screen
│       ├── chat.py             # Chat Screen
│       └── settings.py         # Settings Screen
└── assets/
    ├── icon.png                # App Icon (512x512)
    └── splash.png              # Splash Screen
```

## Development

### Desktop Test

```bash
# Dependencies installieren
pip install -r requirements.txt

# App starten (Desktop-Preview)
python main.py
```

### Android Build

```bash
# Buildozer installieren
pip install buildozer

# Android SDK/NDK Setup (einmalig)
buildozer android debug

# APK bauen
buildozer android debug

# Signierte Release-APK
buildozer android release
```

### Build-Voraussetzungen

- Python 3.9+
- Java JDK 17
- Android SDK (API 34)
- Android NDK 25b
- ~5GB Disk für Android Tools

## APK installieren

```bash
# Via ADB
adb install bin/ailinux-1.0.0-arm64-v8a-debug.apk

# Oder APK direkt auf Gerät kopieren und installieren
```

## Backend-API

Die App kommuniziert mit:

- **Server:** `https://api.ailinux.me`
- **Auth:** `/v1/auth/login`
- **Chat:** `/v1/client/chat`
- **Models:** `/v1/client/models`

## Icons erstellen

```bash
# Icon (512x512 PNG)
cp /path/to/icon.png assets/icon.png

# Splash (1080x1920 oder 9:16)
cp /path/to/splash.png assets/splash.png
```

## Troubleshooting

### Build-Fehler

```bash
# Clean Build
buildozer android clean
buildozer android debug

# Logs
buildozer android debug 2>&1 | tee build.log
```

### Netzwerk-Fehler

- Prüfen ob INTERNET Permission gesetzt ist
- Prüfen ob Server erreichbar ist
- SSL-Zertifikate sind via `certifi` inkludiert

## Version

- **App:** 1.0.0
- **Kivy:** 2.3.0
- **KivyMD:** 1.2.0
- **Target API:** 34 (Android 14)
- **Min API:** 24 (Android 7.0)
