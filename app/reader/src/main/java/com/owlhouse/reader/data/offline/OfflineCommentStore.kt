package com.owlhouse.reader.data.offline

import android.content.Context
import com.owlhouse.reader.data.api.CommentOut
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.builtins.ListSerializer
import java.io.File

/**
 * 按 pageId + sort（latest/hot）缓存评论树。
 */
class OfflineCommentStore(context: Context) {
    private val dir = File(context.filesDir, "offline/comments").also { it.mkdirs() }
    private val mutex = Mutex()
    private val serializer = ListSerializer(CommentOut.serializer())

    suspend fun get(pageId: Int, sort: String): List<CommentOut>? = withContext(Dispatchers.IO) {
        mutex.withLock {
            val file = fileFor(pageId, sort)
            if (!file.exists()) return@withLock null
            try {
                val text = file.readText()
                if (text.isBlank()) return@withLock null
                OfflineJson.decodeFromString(serializer, text)
            } catch (_: Exception) {
                null
            }
        }
    }

    suspend fun put(pageId: Int, sort: String, comments: List<CommentOut>) = withContext(Dispatchers.IO) {
        mutex.withLock {
            fileFor(pageId, sort).writeText(OfflineJson.encodeToString(serializer, comments))
        }
    }

    private fun fileFor(pageId: Int, sort: String): File {
        val safeSort = sort.filter { it.isLetterOrDigit() || it == '_' || it == '-' }.ifBlank { "latest" }
        return File(dir, "${pageId}_$safeSort.json")
    }
}
