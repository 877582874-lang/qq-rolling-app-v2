[app]
title = 滚动历史统计
package.name = qqrolling
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,requests,urllib3,charset-normalizer,idna,certifi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21

[buildozer]
log_level = 2
warn_on_root = 1
