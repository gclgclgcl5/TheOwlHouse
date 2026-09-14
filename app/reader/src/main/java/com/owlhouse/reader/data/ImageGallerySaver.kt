package com.owlhouse.reader.data

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.Locale

object ImageGallerySaver {
    private val http = OkHttpClient()

    /**
     * 下载网络图片并写入系统相册「Pictures/OwlHouse」。
     * @return 成功提示文案；失败抛异常。
     */
    suspend fun saveFromUrl(
        context: Context,
        imageUrl: String,
        displayName: String,
    ): String = withContext(Dispatchers.IO) {
        val request = Request.Builder().url(imageUrl).get().build()
        http.newCall(request).execute().use { resp ->
            if (!resp.isSuccessful) {
                error("下载失败（${resp.code}）")
            }
            val body = resp.body ?: error("下载失败：空响应")
            val bytes = body.bytes()
            val mime = body.contentType()?.toString()
                ?: guessMime(imageUrl)
            val filename = sanitizeFilename(displayName, mime)
            writeToGallery(context, filename, mime, bytes)
            "已保存到相册"
        }
    }

    private fun guessMime(url: String): String {
        val path = url.substringBefore('?').lowercase(Locale.US)
        return when {
            path.endsWith(".png") -> "image/png"
            path.endsWith(".webp") -> "image/webp"
            path.endsWith(".gif") -> "image/gif"
            else -> "image/jpeg"
        }
    }

    private fun extForMime(mime: String): String = when {
        mime.contains("png") -> "png"
        mime.contains("webp") -> "webp"
        mime.contains("gif") -> "gif"
        else -> "jpg"
    }

    private fun sanitizeFilename(raw: String, mime: String): String {
        val ext = extForMime(mime)
        val base = raw.replace(Regex("""[\\/:*?"<>|]"""), "_")
            .trim()
            .ifBlank { "comic" }
            .take(80)
        return if (base.contains('.')) base else "$base.$ext"
    }

    private fun writeToGallery(
        context: Context,
        filename: String,
        mime: String,
        bytes: ByteArray,
    ) {
        val resolver = context.contentResolver
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, filename)
                put(MediaStore.Images.Media.MIME_TYPE, mime)
                put(
                    MediaStore.Images.Media.RELATIVE_PATH,
                    Environment.DIRECTORY_PICTURES + "/OwlHouse",
                )
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: error("无法创建相册条目")
            resolver.openOutputStream(uri)?.use { it.write(bytes) }
                ?: error("无法写入相册")
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        } else {
            @Suppress("DEPRECATION")
            val dir = File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES),
                "OwlHouse",
            )
            if (!dir.exists() && !dir.mkdirs()) {
                error("无法创建相册目录")
            }
            val file = File(dir, filename)
            FileOutputStream(file).use { it.write(bytes) }
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DATA, file.absolutePath)
                put(MediaStore.Images.Media.DISPLAY_NAME, filename)
                put(MediaStore.Images.Media.MIME_TYPE, mime)
            }
            resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
        }
    }
}
