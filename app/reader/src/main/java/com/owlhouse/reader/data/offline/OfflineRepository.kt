package com.owlhouse.reader.data.offline

import android.content.Context
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.api.ComicPageListOut
import com.owlhouse.reader.data.api.ComicPageOut
import com.owlhouse.reader.data.api.CommentOut
import java.io.File

data class CachedResult<T>(
    val data: T,
    val fromCache: Boolean,
)

/**
 * 网络优先的只读离线缓存：成功写盘；失败且有本地数据则回退并标记 fromCache。
 */
class OfflineRepository(context: Context) {
    private val pages = OfflinePageStore(context)
    private val comments = OfflineCommentStore(context)
    private val images = OfflineImageStore(context)

    suspend fun listPages(
        limit: Int = 20,
        offset: Int = 0,
        order: String = "page_no",
    ): CachedResult<ComicPageListOut> {
        return try {
            val res = ApiClient.api.listPages(limit = limit, offset = offset, order = order)
            pages.upsertAll(res.items)
            CachedResult(res, fromCache = false)
        } catch (e: Exception) {
            val (items, total) = pages.slice(offset, limit)
            if (items.isEmpty() && total == 0 && offset == 0) throw e
            if (items.isEmpty() && offset > 0 && total > 0) {
                // 已到缓存末尾：返回空页而非抛错，便于分页循环结束
                return CachedResult(
                    ComicPageListOut(items = emptyList(), total = total, limit = limit, offset = offset),
                    fromCache = true,
                )
            }
            if (items.isEmpty()) throw e
            CachedResult(
                ComicPageListOut(items = items, total = total, limit = limit, offset = offset),
                fromCache = true,
            )
        }
    }

    suspend fun getPage(id: Int): CachedResult<ComicPageOut> {
        return try {
            val page = ApiClient.api.getPage(id)
            pages.upsertAll(listOf(page))
            CachedResult(page, fromCache = false)
        } catch (e: Exception) {
            val cached = pages.get(id) ?: throw e
            CachedResult(cached, fromCache = true)
        }
    }

    suspend fun listComments(pageId: Int, sort: String = "latest"): CachedResult<List<CommentOut>> {
        return try {
            val items = ApiClient.api.listComments(pageId, sort = sort).items
            comments.put(pageId, sort, items)
            CachedResult(items, fromCache = false)
        } catch (e: Exception) {
            val cached = comments.get(pageId, sort) ?: throw e
            CachedResult(cached, fromCache = true)
        }
    }

    /** 在线时下载页图；失败静默（保留旧文件若有）。 */
    suspend fun ensurePageImage(page: ComicPageOut): File? {
        return try {
            images.ensureCached(page)
        } catch (_: Exception) {
            images.localFile(page.id)
        }
    }

    fun localImageFile(pageId: Int): File? = images.localFile(pageId)

    /** Coil / AsyncImage 用：优先本地文件，否则网络 URL。 */
    fun imageModel(page: ComicPageOut): Any {
        val local = images.localFile(page.id)
        if (local != null) return local
        return com.owlhouse.reader.config.AppConfig.mediaUrl(page.imageUrl)
    }
}
