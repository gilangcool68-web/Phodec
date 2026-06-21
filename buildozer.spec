[app]

# (str) Title of your application
title = Phodec

# (str) Package name
package.name = photodetectorapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (leave empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,pxi

# (str) Application versioning (method 1)
version = 0.1

# (str) Icon of the application
icon.filename = uploads/icon.png

# (list) Application requirements
# Updated Kivy to 2.3.0 for better NDK 25b compatibility
# Pin Python to 3.11 because Kivy 2.3.0 is not compatible with CPython 3.14 C-API changes
requirements = python3.11,kivy==2.3.0,kivymd==0.104.2,requests==2.31.0,plyer,pyjnius

# (list) Supported orientations
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
# PENTING: Pagar dilepas agar aplikasi diizinkan mengambil GPS dan Kamera HP
android.permissions = CAMERA, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, REQUEST_INSTALL_PACKAGES

# (int) Target Android API
# Dikunci ke API 31 & Build Tools 31 agar server GitHub tidak memicu download versi 37 yang lisensinya mampet
android.api = 31
android.build_tools_version = 31.0.0

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (int) Android NDK API to use.
android.ndk_api = 21

# (str) Android NDK version to use
# DIKUNCI KE 25b AGAR TIDAK CRASH DENGAN PYTHON-FOR-ANDROID
android.ndk = 25b

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature
android.allow_backup = True

# (bool) Otomatis terima lisensi SDK (INI YANG BIKIN AIDL BISA TER-INSTALL)
android.accept_sdk_license = True

#
# iOS specific
#
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.12.2
ios.codesign.allowed = false

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
