# The Owl House · Android App

Kotlin + Jetpack Compose 用户端。用 **Android Studio** 打开本目录（`TheOwlHouse/app`）。

## 能力（MVP）

注册/登录、漫画列表下拉刷新、沉浸阅读（点图出控件、左右滑翻页）、底部评论面板（最新/最热、回复、点赞）、消息中心与未读角标。401 自动清 Token 退登。

## 工程版本

- Gradle **8.6** · AGP **8.4.2** · compileSdk **34**
- Kotlin **1.9.24** · Compose Compiler **1.5.14**

## 服务器地址

当前 `API_BASE_URL` 指向生产：`http://101.132.75.57/`。局域网联调时改回 `http://<电脑IP>:8000/`。

打包：

```powershell
cd app
.\gradlew.bat :reader:assembleDebug
```

APK：`reader/build/outputs/apk/debug/reader-debug.apk`

## 自定义图标

见 `reader/branding/`：放入 `app_icon.png` 后执行 `python apply_icon.py`，再重装 App。
