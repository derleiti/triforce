[app]
title = AILinux Client
package.name = ailinux
package.domain = me.ailinux
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0
requirements = python3,kivy==2.3.0,kivymd==1.2.0,httpx,certifi,pillow
orientation = portrait
fullscreen = 0

# Android specific
android.permissions = INTERNET,ACCESS_NETWORK_STATE,VIBRATE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

# Icons
icon.filename = assets/icon.png
presplash.filename = assets/splash.png

# Build
log_level = 2
warn_on_root = 0

[buildozer]
log_level = 2
warn_on_root = 0
