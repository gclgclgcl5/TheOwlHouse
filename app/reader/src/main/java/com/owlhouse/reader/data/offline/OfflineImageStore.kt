package com.owlhouse.reader.data.offline

import android.content.Context
import android.content.SharedPreferences
import com.owlhouse.reader.config.AppConfig
import com.owlhouse.reader.data.api.ComicPageOut
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * 页图下载到 app 私有目录；用 updatedAt + imageUrl 判断是否需要重下。
 */
class OfflineImageStore(context: Context) {
    private val appContext = context.applicationContext
    private val dir = File(appContext.filesDir, "offline/images").also { it.mkdirs() }
    private val meta: SharedPreferences =
        appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    fun localFile(pageId: Int): File? {
        val name = meta.getString(keyFile(pageId), null) ?: return null
        val file = File(dir, name)
        return file.takeIf { it.isFile && it.length() > 0 }
    }

    suspend fun ensureCached(page: ComicPageOut): File? = withContext(Dispatchers.IO) {
        val stamp = stampOf(page)
        val existing = localFile(page.id)
        val cachedStamp = meta.getString(keyStamp(page.id), null)
        if (existing != null && cachedStamp == stamp) {
            return@withContext existing
        }

        val url = AppConfig.mediaUrl(page.imageUrl)
        val request = Request.Builder().url(url).get().build()
        http.newCall(request).execute().use { resp ->
            if (!resp.isSuccessful) return@withContext existing
            val body = resp.body ?: return@withContext existing
            val bytes = body.bytes()
            if (bytes.isEmpty()) return@withContext existing
            val mime = body.contentType()?.toString() ?: guessMime(url)
            val ext = extForMime(mime)
            val filename = "${page.id}.$ext"
            val target = File(dir, filename)
            // 清理同 pageId 旧扩展名文件
            dir.listFiles()?.forEach { f ->
                if (f.name.startsWith("${page.id}.") && f.name != filename) {
                    f.delete()
                }
            }
            target.writeBytes(bytes)
            meta.edit()
                .putString(keyFile(page.id), filename)
                .putString(keyStamp(page.id), stamp)
                .apply()
            target
        }
    }

    private fun stampOf(page: ComicPageOut): String = "${page.updatedAt}|${page.imageUrl}"

    private fun keyFile(pageId: Int) = "file_$pageId"
    private fun keyStamp(pageId: Int) = "stamp_$pageId"

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

    companion object {
        private const val PREFS = "owlhouse_offline_images"
    }
}
