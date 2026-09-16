package com.owlhouse.reader.data.offline

import android.content.Context
import com.owlhouse.reader.data.api.ComicPageOut
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.builtins.ListSerializer
import java.io.File

/**
 * 页元数据本地缓存：按 id upsert，列表按 page_no、id 排序。
 */
class OfflinePageStore(context: Context) {
    private val root = File(context.filesDir, "offline").also { it.mkdirs() }
    private val file = File(root, "pages.json")
    private val mutex = Mutex()
    private val serializer = ListSerializer(ComicPageOut.serializer())

    suspend fun all(): List<ComicPageOut> = withContext(Dispatchers.IO) {
        mutex.withLock { readUnlocked() }
    }

    suspend fun get(id: Int): ComicPageOut? = all().firstOrNull { it.id == id }

    suspend fun slice(offset: Int, limit: Int): Pair<List<ComicPageOut>, Int> {
        val all = all()
        val safeOffset = offset.coerceAtLeast(0)
        val items = if (safeOffset >= all.size) {
            emptyList()
        } else {
            all.subList(safeOffset, (safeOffset + limit).coerceAtMost(all.size))
        }
        return items to all.size
    }

    suspend fun upsertAll(pages: List<ComicPageOut>) = withContext(Dispatchers.IO) {
        if (pages.isEmpty()) return@withContext
        mutex.withLock {
            val map = readUnlocked().associateBy { it.id }.toMutableMap()
            for (p in pages) {
                map[p.id] = p
            }
            writeUnlocked(map.values.sortedWith(compareBy({ it.pageNo }, { it.id })))
        }
    }

    private fun readUnlocked(): List<ComicPageOut> {
        if (!file.exists()) return emptyList()
        return try {
            val text = file.readText()
            if (text.isBlank()) emptyList()
            else OfflineJson.decodeFromString(serializer, text)
                .sortedWith(compareBy({ it.pageNo }, { it.id }))
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeUnlocked(pages: List<ComicPageOut>) {
        file.writeText(OfflineJson.encodeToString(serializer, pages))
    }
}
