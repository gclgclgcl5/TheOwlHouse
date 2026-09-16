package com.owlhouse.reader.ui.pages

import com.owlhouse.reader.OwlHouseApp
import com.owlhouse.reader.config.AppConfig
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.api.ComicPageOut
import com.owlhouse.reader.data.api.CommentCreate
import com.owlhouse.reader.data.api.CommentOut

data class ReaderPage(
    val id: Int,
    val title: String,
    val pageNo: Int,
    val imageUrl: String,
    val subtitle: String? = null,
)

data class ReaderBootstrap(
    val pages: List<ReaderPage>,
    val initialPageId: Int,
    val catalogTotal: Int,
    val catalogHasMore: Boolean,
    val nextOffset: Int,
    val fromCache: Boolean = false,
    val switchMessage: String? = null,
)

data class ReaderCatalogChunk(
    val pages: List<ReaderPage>,
    val catalogTotal: Int,
    val nextOffset: Int,
    val catalogHasMore: Boolean,
    val fromCache: Boolean = false,
)

data class ReaderCommentsResult(
    val items: List<CommentOut>,
    val fromCache: Boolean = false,
)

interface ReaderSource {
    val supportsOffline: Boolean
    suspend fun bootstrap(): ReaderBootstrap
    suspend fun loadMoreCatalog(
        current: List<ReaderPage>,
        nextOffset: Int,
    ): ReaderCatalogChunk

    suspend fun listComments(pageId: Int, sort: String): ReaderCommentsResult
    suspend fun createComment(pageId: Int, body: CommentCreate): CommentOut
    fun markRead(page: ReaderPage)
    fun imageModel(page: ReaderPage): Any
    suspend fun ensureImage(page: ReaderPage)
}

private const val READER_PAGE_BATCH = 40

private fun ComicPageOut.toReaderPage(): ReaderPage = ReaderPage(
    id = id,
    title = title,
    pageNo = pageNo,
    imageUrl = imageUrl,
)

private fun ReaderPage.toComicPageOut(): ComicPageOut = ComicPageOut(
    id = id,
    title = title,
    pageNo = pageNo,
    imageUrl = imageUrl,
    createdAt = "",
    updatedAt = "",
)

class DoujinReaderSource(
    private val app: OwlHouseApp,
    private val startPageId: Int,
) : ReaderSource {
    override val supportsOffline: Boolean = true

    override suspend fun bootstrap(): ReaderBootstrap {
        val loaded = mutableListOf<ComicPageOut>()
        var loadedCount = 0
        var total = 0
        var fromCache = false
        while (true) {
            val cached = app.offline.listPages(
                limit = READER_PAGE_BATCH,
                offset = loadedCount,
                order = "page_no",
            )
            if (cached.fromCache) fromCache = true
            val res = cached.data
            if (res.items.isEmpty()) break
            loaded += res.items
            total = res.total
            loadedCount += res.items.size
            if (loaded.any { it.id == startPageId }) break
            if (loadedCount >= total) break
        }
        var pages = if (loaded.isEmpty()) {
            emptyList()
        } else {
            loaded.distinctBy { it.id }.sortedBy { it.pageNo }
        }
        if (pages.isNotEmpty() && pages.none { it.id == startPageId }) {
            val one = app.offline.getPage(startPageId)
            if (one.fromCache) fromCache = true
            pages = (pages + one.data).distinctBy { it.id }.sortedBy { it.pageNo }
        }
        val readerPages = pages.map { it.toReaderPage() }
        val catalogTotal = maxOf(total, readerPages.size)
        return ReaderBootstrap(
            pages = readerPages,
            initialPageId = startPageId,
            catalogTotal = catalogTotal,
            catalogHasMore = loadedCount < catalogTotal,
            nextOffset = loadedCount,
            fromCache = fromCache,
        )
    }

    override suspend fun loadMoreCatalog(
        current: List<ReaderPage>,
        nextOffset: Int,
    ): ReaderCatalogChunk {
        val cached = app.offline.listPages(
            limit = READER_PAGE_BATCH,
            offset = nextOffset,
            order = "page_no",
        )
        val res = cached.data
        if (res.items.isEmpty()) {
            return ReaderCatalogChunk(
                pages = current,
                catalogTotal = maxOf(current.size, res.total),
                nextOffset = nextOffset,
                catalogHasMore = false,
                fromCache = cached.fromCache,
            )
        }
        val merged = (current + res.items.map { it.toReaderPage() })
            .distinctBy { it.id }
            .sortedBy { it.pageNo }
        val newOffset = nextOffset + res.items.size
        val catalogTotal = maxOf(merged.size, res.total)
        return ReaderCatalogChunk(
            pages = merged,
            catalogTotal = catalogTotal,
            nextOffset = newOffset,
            catalogHasMore = newOffset < catalogTotal,
            fromCache = cached.fromCache,
        )
    }

    override suspend fun listComments(pageId: Int, sort: String): ReaderCommentsResult {
        val cached = app.offline.listComments(pageId, sort = sort)
        return ReaderCommentsResult(items = cached.data, fromCache = cached.fromCache)
    }

    override suspend fun createComment(pageId: Int, body: CommentCreate): CommentOut {
        return ApiClient.api.createComment(pageId, body)
    }

    override fun markRead(page: ReaderPage) {
        app.readingProgress.markRead(page.toComicPageOut())
    }

    override fun imageModel(page: ReaderPage): Any {
        return app.offline.imageModel(page.toComicPageOut())
    }

    override suspend fun ensureImage(page: ReaderPage) {
        app.offline.ensurePageImage(page.toComicPageOut())
    }
}

class KingReaderSource(
    private val app: OwlHouseApp,
    private val versionId: Int,
    private val slotId: Int,
) : ReaderSource {
    override val supportsOffline: Boolean = false

    private var activeVersionId: Int = versionId
    private var versionName: String = ""

    override suspend fun bootstrap(): ReaderBootstrap {
        val preferred = versionId
        val resolved = if (slotId > 0) {
            ApiClient.api.resolveKingPage(
                slotId = slotId,
                preferredVersionId = preferred,
            )
        } else {
            val pageNo = app.kingProgress.lastPageNo.coerceAtLeast(1)
            ApiClient.api.resolveKingPage(
                pageNo = pageNo,
                preferredVersionId = preferred,
            )
        }
        activeVersionId = resolved.versionId
        versionName = resolved.versionName
        app.kingProgress.markRead(
            slotId = resolved.slotId,
            pageNo = resolved.pageNo,
            title = resolved.title,
            versionId = resolved.versionId,
        )
        val list = ApiClient.api.listKingVersionPages(resolved.versionId)
        versionName = list.versionName.ifBlank { resolved.versionName }
        val pages = list.items.map { item ->
            ReaderPage(
                id = item.slotId,
                title = item.title,
                pageNo = item.pageNo,
                imageUrl = item.imageUrl,
                subtitle = versionName,
            )
        }
        val switchMessage = if (resolved.switched) {
            "已切换到「${resolved.versionName}」"
        } else {
            null
        }
        return ReaderBootstrap(
            pages = pages,
            initialPageId = resolved.slotId,
            catalogTotal = pages.size,
            catalogHasMore = false,
            nextOffset = pages.size,
            switchMessage = switchMessage,
        )
    }

    override suspend fun loadMoreCatalog(
        current: List<ReaderPage>,
        nextOffset: Int,
    ): ReaderCatalogChunk {
        return ReaderCatalogChunk(
            pages = current,
            catalogTotal = current.size,
            nextOffset = nextOffset,
            catalogHasMore = false,
        )
    }

    override suspend fun listComments(pageId: Int, sort: String): ReaderCommentsResult {
        val items = ApiClient.api.listKingComments(pageId, sort = sort).items
        return ReaderCommentsResult(items = items, fromCache = false)
    }

    override suspend fun createComment(pageId: Int, body: CommentCreate): CommentOut {
        return ApiClient.api.createKingComment(pageId, body)
    }

    override fun markRead(page: ReaderPage) {
        app.kingProgress.markRead(
            slotId = page.id,
            pageNo = page.pageNo,
            title = page.title,
            versionId = activeVersionId,
        )
    }

    override fun imageModel(page: ReaderPage): Any {
        return AppConfig.mediaUrl(page.imageUrl)
    }

    override suspend fun ensureImage(page: ReaderPage) {
        // King 本期不做离线预取
    }
}
