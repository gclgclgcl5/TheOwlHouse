package com.owlhouse.reader.ui.update

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import com.owlhouse.reader.BuildConfig
import com.owlhouse.reader.OwlHouseApp
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.api.AppUpdateOut

private const val UPDATE_SNOOZE_HOURS = 24L
private const val UPDATE_SNOOZE_MS = UPDATE_SNOOZE_HOURS * 60L * 60L * 1000L

/**
 * 进入首页后拉取后台版本配置；若远端 versionCode 更大则弹窗，并提供复制下载链接。
 */
@Composable
fun AppUpdatePrompt() {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    var pending by remember { mutableStateOf<AppUpdateOut?>(null) }
    var copied by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        if (app.updateCheckedThisLaunch) return@LaunchedEffect
        app.updateCheckedThisLaunch = true
        val now = System.currentTimeMillis()
        if (now < app.updatePrefs.snoozeUntilMs) return@LaunchedEffect
        try {
            val remote = ApiClient.api.getAppUpdate()
            if (!remote.available) return@LaunchedEffect
            if (remote.versionCode <= BuildConfig.VERSION_CODE) return@LaunchedEffect
            // 兼容历史永久忽略逻辑：仅对旧版本数据生效，不再写入。
            if (remote.versionCode <= app.updatePrefs.ignoredVersionCode) return@LaunchedEffect
            if (remote.downloadUrl.isBlank()) return@LaunchedEffect
            pending = remote
        } catch (_: Exception) {
            // 更新检查失败不打断使用
        }
    }

    val info = pending ?: return

    val titleVersion = info.versionName.ifBlank { info.versionCode.toString() }
    val body = buildString {
        append("发现新版本 ")
        append(titleVersion)
        append("（当前 ")
        append(BuildConfig.VERSION_NAME)
        append("）。\n\n")
        if (info.message.isNotBlank()) {
            append(info.message.trim())
            append("\n\n")
        }
        append("请复制下载链接，在浏览器中打开并安装。")
        if (copied) {
            append("\n\n已复制到剪贴板。")
        }
    }

    AlertDialog(
        onDismissRequest = {
            if (copied) pending = null
        },
        title = { Text("可以更新了") },
        text = {
            Text(
                text = body,
                textAlign = TextAlign.Start,
            )
        },
        confirmButton = {
            TextButton(
                onClick = {
                    copyDownloadUrl(context, info.downloadUrl)
                    copied = true
                    Toast.makeText(context, "下载链接已复制", Toast.LENGTH_SHORT).show()
                },
            ) {
                Text(if (copied) "再次复制链接" else "复制下载链接")
            }
        },
        dismissButton = {
            TextButton(
                onClick = {
                    if (!copied) {
                        app.updatePrefs.snoozedVersionCode = info.versionCode
                        app.updatePrefs.snoozeUntilMs = System.currentTimeMillis() + UPDATE_SNOOZE_MS
                    }
                    pending = null
                },
            ) {
                Text(if (copied) "关闭" else "24小时后提醒")
            }
        },
    )
}

private fun copyDownloadUrl(context: Context, url: String) {
    val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    cm.setPrimaryClip(ClipData.newPlainText("download_url", url))
}
