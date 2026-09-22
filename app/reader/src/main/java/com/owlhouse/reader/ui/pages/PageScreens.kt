@file:OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)

package com.owlhouse.reader.ui.pages

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.core.content.ContextCompat
import androidx.compose.foundation.basicMarquee
import androidx.compose.foundation.clickable
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Fullscreen
import androidx.compose.material.icons.filled.ChatBubble
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Layers
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material.icons.outlined.Layers
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.FloatingActionButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.zIndex
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import coil.compose.AsyncImage
import com.owlhouse.reader.OwlHouseApp
import com.owlhouse.reader.config.AppConfig
import com.owlhouse.reader.data.HomeTabStore
import com.owlhouse.reader.data.ImageGallerySaver
import com.owlhouse.reader.data.ReaderDisplayMode
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.api.ComicPageOut
import com.owlhouse.reader.data.api.CommentCreate
import com.owlhouse.reader.data.api.CommentOut
import com.owlhouse.reader.data.api.KingVersionOut
import com.owlhouse.reader.data.api.userFacingError
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

private const val LIST_PAGE_SIZE = 20

/** 标题完全一致的合集（封面 = page_no 最小）。 */
private data class TitleCollection(
    val title: String,
    val cover: ComicPageOut,
    val pages: List<ComicPageOut>,
) {
    val count: Int get() = pages.size
}

private fun groupPagesByExactTitle(pages: List<ComicPageOut>): List<TitleCollection> {
    return pages
        .groupBy { it.title }
        .map { (title, list) ->
            val sorted = list.sortedWith(compareBy({ it.pageNo }, { it.id }))
            TitleCollection(title = title, cover = sorted.first(), pages = sorted)
        }
        .sortedWith(compareBy({ it.cover.pageNo }, { it.cover.id }))
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalMaterialApi::class)
@Composable
fun PageListScreen(
    onOpenPage: (Int) -> Unit,
    onOpenKing: (versionId: Int, slotId: Int) -> Unit,
    onOpenKingPages: (versionId: Int) -> Unit,
    onOpenNotifications: () -> Unit,
    onLogout: () -> Unit,
    onSessionExpired: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    val scope = rememberCoroutineScope()
    var homeTab by remember { mutableStateOf(app.homeTab.tab) }
    var pages by remember { mutableStateOf<List<ComicPageOut>>(emptyList()) }
    var kingVersions by remember { mutableStateOf<List<KingVersionOut>>(emptyList()) }
    var total by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var refreshing by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(true) }
    var loadingMore by remember { mutableStateOf(false) }
    var unread by remember { mutableIntStateOf(0) }
    var homeTitle by remember { mutableStateOf(app.homeAnnouncement.displayedTitle) }
    var confirmLogout by remember { mutableStateOf(false) }
    var doujinCollectionMode by remember { mutableStateOf(app.collectionMode.doujinEnabled) }
    var kingCollectionMode by remember { mutableStateOf(app.collectionMode.kingEnabled) }
    var lastPageId by remember { mutableIntStateOf(app.readingProgress.lastPageId) }
    var lastPageNo by remember { mutableIntStateOf(app.readingProgress.lastPageNo) }
    var lastTitle by remember { mutableStateOf(app.readingProgress.lastTitle) }
    var lastKingVersionId by remember { mutableIntStateOf(app.kingProgress.lastVersionId) }
    var syncingToProgress by remember { mutableStateOf(false) }
    var usingOfflineCache by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val isKingTab = homeTab == HomeTabStore.TAB_KING
    val latestIsKingTab = rememberUpdatedState(isKingTab)
    val collectionMode = if (isKingTab) kingCollectionMode else doujinCollectionMode

    fun reloadProgress() {
        lastPageId = app.readingProgress.lastPageId
        lastPageNo = app.readingProgress.lastPageNo
        lastTitle = app.readingProgress.lastTitle
        lastKingVersionId = app.kingProgress.lastVersionId
    }

    fun noteOfflineCache(fromCache: Boolean) {
        if (fromCache) {
            usingOfflineCache = true
            if (!app.offlineHintShownThisProcess) {
                app.offlineHintShownThisProcess = true
                Toast.makeText(context, "留作纪念，后会有期！", Toast.LENGTH_SHORT).show()
            }
        } else {
            usingOfflineCache = false
        }
    }

    suspend fun fetchPages(offset: Int) =
        app.offline.listPages(limit = LIST_PAGE_SIZE, offset = offset, order = "page_no")

    suspend fun ensureAllPagesLoaded() {
        while (pages.size < total) {
            val res = fetchPages(pages.size)
            noteOfflineCache(res.fromCache)
            if (res.data.items.isEmpty()) break
            pages = pages + res.data.items
            total = res.data.total
        }
    }

    /** 补载到包含进度页，并滚到该列表项（继续阅读卡片占 1 个 index） */
    suspend fun ensureAndScrollToProgress() {
        val targetId = app.readingProgress.lastPageId
        reloadProgress()
        if (targetId <= 0 || pages.isEmpty()) return
        syncingToProgress = true
        try {
            while (pages.none { it.id == targetId } && pages.size < total) {
                val res = fetchPages(pages.size)
                noteOfflineCache(res.fromCache)
                if (res.data.items.isEmpty()) break
                pages = pages + res.data.items
                total = res.data.total
            }
            if (doujinCollectionMode) {
                ensureAllPagesLoaded()
            }
            val listIndex = if (doujinCollectionMode) {
                val collections = groupPagesByExactTitle(pages)
                val idx = collections.indexOfFirst { c -> c.pages.any { it.id == targetId } }
                if (idx < 0) return
                idx + 1
            } else {
                val idxInPages = pages.indexOfFirst { it.id == targetId }
                if (idxInPages < 0) return
                idxInPages + 1
            }
            kotlinx.coroutines.yield()
            listState.scrollToItem(listIndex)
        } finally {
            syncingToProgress = false
        }
    }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                reloadProgress()
                scope.launch {
                    if (!latestIsKingTab.value && !loading && pages.isNotEmpty()) {
                        ensureAndScrollToProgress()
                    }
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    fun refreshUnread() {
        scope.launch {
            try {
                unread = ApiClient.api.unreadCount().count
            } catch (_: Exception) {
                // 未读角标失败不打断首页
            }
        }
    }

    suspend fun refreshMeta() {
        try {
            unread = ApiClient.api.unreadCount().count
        } catch (_: Exception) {
            // 未读角标失败不打断首页
        }
        try {
            val announcement = ApiClient.api.getHomeAnnouncement()
            val remote = announcement.title.trim()
            if (remote.isNotBlank()) {
                app.homeAnnouncement.title = remote
                homeTitle = remote
            }
        } catch (_: Exception) {
            // 公告拉取失败时保留缓存/当前标题
        }
    }

    fun refreshKing() {
        scope.launch {
            refreshing = true
            error = null
            try {
                kingVersions = ApiClient.api.listKingVersions().items
                refreshMeta()
                reloadProgress()
            } catch (e: Exception) {
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                    return@launch
                }
                error = userFacingError(e, "加载失败")
            } finally {
                refreshing = false
                loading = false
            }
        }
    }

    fun refreshDoujin() {
        scope.launch {
            refreshing = true
            error = null
            var ok = false
            try {
                val res = fetchPages(0)
                noteOfflineCache(res.fromCache)
                pages = res.data.items
                total = res.data.total
                if (!res.fromCache) {
                    refreshMeta()
                }
                if (doujinCollectionMode) {
                    ensureAllPagesLoaded()
                }
                reloadProgress()
                ok = true
            } catch (e: Exception) {
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                    return@launch
                }
                error = userFacingError(e, "加载失败")
            } finally {
                refreshing = false
                loading = false
            }
            if (ok) {
                kotlinx.coroutines.yield()
                ensureAndScrollToProgress()
            }
        }
    }

    fun refresh(forTab: String = homeTab) {
        if (forTab == HomeTabStore.TAB_KING) refreshKing() else refreshDoujin()
    }

    fun switchTab(tab: String) {
        val next = if (tab == HomeTabStore.TAB_KING) HomeTabStore.TAB_KING else HomeTabStore.TAB_DOUJIN
        if (next == homeTab) return
        homeTab = next
        app.homeTab.tab = next
        loading = true
        error = null
        refresh(next)
    }

    fun loadMore() {
        if (isKingTab || doujinCollectionMode) return
        if (loadingMore || refreshing || loading || syncingToProgress || pages.isEmpty()) return
        if (pages.size >= total) return
        scope.launch {
            loadingMore = true
            try {
                val res = fetchPages(pages.size)
                noteOfflineCache(res.fromCache)
                pages = pages + res.data.items
                total = res.data.total
            } catch (e: Exception) {
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                    return@launch
                }
                error = userFacingError(e, "加载更多失败")
            } finally {
                loadingMore = false
            }
        }
    }

    fun setCollectionMode(on: Boolean) {
        if (isKingTab) {
            kingCollectionMode = on
            app.collectionMode.kingEnabled = on
            return
        }
        doujinCollectionMode = on
        app.collectionMode.doujinEnabled = on
        if (on) {
            scope.launch {
                try {
                    ensureAllPagesLoaded()
                } catch (e: Exception) {
                    if (!app.tokenStore.isLoggedIn) {
                        onSessionExpired()
                        return@launch
                    }
                    error = userFacingError(e, "加载合集失败")
                }
            }
        }
    }

    fun openCollection(collection: TitleCollection) {
        val progressHit = collection.pages.firstOrNull { it.id == lastPageId }
        onOpenPage(progressHit?.id ?: collection.cover.id)
    }

    LaunchedEffect(Unit) {
        refresh()
        while (true) {
            delay(20_000)
            refreshUnread()
        }
    }

    LaunchedEffect(listState, isKingTab, doujinCollectionMode) {
        if (isKingTab) return@LaunchedEffect
        snapshotFlow {
            val info = listState.layoutInfo
            val lastVisible = info.visibleItemsInfo.lastOrNull()?.index ?: 0
            val totalItems = info.totalItemsCount
            lastVisible to totalItems
        }
            .distinctUntilChanged()
            .collect { (lastVisible, totalItems) ->
                if (!doujinCollectionMode && totalItems > 0 && lastVisible >= totalItems - 3) {
                    loadMore()
                }
            }
    }

    val pullState = rememberPullRefreshState(refreshing, onRefresh = { refresh() })
    val hasProgress = !isKingTab && lastPageId > 0
    val endReached = !isKingTab && pages.isNotEmpty() && pages.size >= total && total > 0
    val collections = remember(pages, doujinCollectionMode, isKingTab) {
        if (!isKingTab && doujinCollectionMode) groupPagesByExactTitle(pages) else emptyList()
    }
    val selectedTabIndex = if (isKingTab) 1 else 0

    if (confirmLogout) {
        AlertDialog(
            onDismissRequest = { confirmLogout = false },
            title = { Text("退出登录") },
            text = { Text("确定要退出当前账号吗？") },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirmLogout = false
                        app.tokenStore.clear()
                        onLogout()
                    },
                ) {
                    Text("退出")
                }
            },
            dismissButton = {
                TextButton(onClick = { confirmLogout = false }) {
                    Text("取消")
                }
            },
        )
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.background)
                    .statusBarsPadding(),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(64.dp)
                        .padding(end = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = homeTitle,
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onBackground,
                        maxLines = 1,
                        softWrap = false,
                        modifier = Modifier
                            .weight(1f)
                            .padding(start = 16.dp)
                            .basicMarquee(iterations = Int.MAX_VALUE),
                    )
                    IconButton(
                        onClick = { setCollectionMode(!collectionMode) },
                        modifier = Modifier.size(48.dp),
                    ) {
                        Icon(
                            imageVector = if (collectionMode) Icons.Filled.Layers else Icons.Outlined.Layers,
                            contentDescription = if (collectionMode) "合集模式已开" else "合集模式",
                            tint = if (collectionMode) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onBackground
                            },
                            modifier = Modifier.size(26.dp),
                        )
                    }
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .clickable(onClick = onOpenNotifications),
                        contentAlignment = Alignment.Center,
                    ) {
                        BadgedBox(
                            badge = {
                                if (unread > 0) {
                                    Badge(
                                        containerColor = MaterialTheme.colorScheme.tertiary,
                                        contentColor = MaterialTheme.colorScheme.onTertiary,
                                    ) {
                                        Text(if (unread > 99) "99+" else unread.toString())
                                    }
                                }
                            },
                        ) {
                            Icon(
                                Icons.Filled.Notifications,
                                contentDescription = "消息",
                                tint = MaterialTheme.colorScheme.onBackground,
                                modifier = Modifier.size(28.dp),
                            )
                        }
                    }
                    IconButton(
                        onClick = { confirmLogout = true },
                        modifier = Modifier.size(48.dp),
                    ) {
                        Icon(
                            Icons.AutoMirrored.Filled.Logout,
                            contentDescription = "退出登录",
                            tint = MaterialTheme.colorScheme.onBackground,
                            modifier = Modifier.size(28.dp),
                        )
                    }
                }
                TabRow(
                    selectedTabIndex = selectedTabIndex,
                    containerColor = MaterialTheme.colorScheme.background,
                    contentColor = MaterialTheme.colorScheme.primary,
                    indicator = { tabPositions ->
                        TabRowDefaults.SecondaryIndicator(
                            modifier = Modifier.tabIndicatorOffset(tabPositions[selectedTabIndex]),
                            color = MaterialTheme.colorScheme.primary,
                        )
                    },
                ) {
                    Tab(
                        selected = !isKingTab,
                        onClick = { switchTab(HomeTabStore.TAB_DOUJIN) },
                        text = { Text("同人漫画") },
                    )
                    Tab(
                        selected = isKingTab,
                        onClick = { switchTab(HomeTabStore.TAB_KING) },
                        text = { Text("长寿之王") },
                    )
                }
            }
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .pullRefresh(pullState),
        ) {
            when {
                loading -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                isKingTab && error != null && kingVersions.isEmpty() -> Box(
                    modifier = Modifier.fillMaxSize().padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(error ?: "", color = MaterialTheme.colorScheme.error)
                }
                isKingTab && kingVersions.isEmpty() -> Box(
                    modifier = Modifier.fillMaxSize().padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("暂无内容，请先在管理后台创建长寿之王版本。")
                }
                isKingTab -> LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    items(kingVersions, key = { it.id }) { version ->
                        KingVersionCard(
                            version = version,
                            isLastRead = lastKingVersionId > 0 && version.id == lastKingVersionId,
                            onClick = {
                                if (kingCollectionMode) onOpenKing(version.id, 0)
                                else onOpenKingPages(version.id)
                            },
                        )
                    }
                }
                error != null && pages.isEmpty() -> Box(
                    modifier = Modifier.fillMaxSize().padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(error ?: "", color = MaterialTheme.colorScheme.error)
                }
                pages.isEmpty() -> Box(
                    modifier = Modifier.fillMaxSize().padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("还没有漫画，请先在管理后台上传。")
                }
                else -> LazyColumn(
                    state = listState,
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    if (hasProgress) {
                        item(key = "continue-reading") {
                            ContinueReadingCard(
                                title = lastTitle.ifBlank { "上次阅读" },
                                onClick = { onOpenPage(lastPageId) },
                            )
                        }
                    }
                    if (doujinCollectionMode) {
                        items(collections, key = { "col-${it.title}-${it.cover.id}" }) { col ->
                            val isCurrent = col.pages.any { it.id == lastPageId }
                            val allRead = lastPageNo > 0 && col.pages.all { it.pageNo <= lastPageNo }
                            CollectionListItem(
                                collection = col,
                                imageModel = app.offline.imageModel(col.cover),
                                isRead = allRead,
                                isCurrent = isCurrent,
                                onClick = { openCollection(col) },
                            )
                        }
                    } else {
                        items(pages, key = { it.id }) { page ->
                            val read = lastPageNo > 0 && page.pageNo <= lastPageNo
                            val isCurrent = page.id == lastPageId
                            PageListItem(
                                page = page,
                                imageModel = app.offline.imageModel(page),
                                isRead = read,
                                isCurrent = isCurrent,
                                onClick = { onOpenPage(page.id) },
                            )
                        }
                    }
                    item(key = "list-footer") {
                        when {
                            loadingMore -> {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 12.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    CircularProgressIndicator(modifier = Modifier.size(28.dp))
                                }
                            }
                            endReached -> {
                                Text(
                                    "没有更多了",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    textAlign = TextAlign.Center,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 8.dp),
                                )
                            }
                        }
                    }
                }
            }
            PullRefreshIndicator(
                refreshing = refreshing,
                state = pullState,
                modifier = Modifier.align(Alignment.TopCenter),
                contentColor = MaterialTheme.colorScheme.primary,
                backgroundColor = MaterialTheme.colorScheme.surface,
            )
        }
    }
}

@Composable
private fun KingVersionCard(
    version: KingVersionOut,
    isLastRead: Boolean,
    onClick: () -> Unit,
) {
    var infoOpen by remember(version.id) { mutableStateOf(false) }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(
                if (isLastRead) {
                    MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.9f)
                } else {
                    MaterialTheme.colorScheme.surface.copy(alpha = 0.72f)
                },
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AsyncImage(
            model = AppConfig.mediaUrl(version.coverUrl),
            contentDescription = version.name,
            modifier = Modifier
                .width(72.dp)
                .height(72.dp)
                .clip(RoundedCornerShape(12.dp)),
            contentScale = ContentScale.Crop,
        )
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = version.name,
                style = MaterialTheme.typography.titleMedium,
                color = if (isLastRead) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurface
                },
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = buildString {
                    append("已上传 ${version.uploadedCount} 页")
                    if (isLastRead) append(" · 上次阅读")
                },
                style = MaterialTheme.typography.labelSmall,
                color = if (isLastRead) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurfaceVariant
                },
                modifier = Modifier.padding(top = 4.dp),
            )
        }
        IconButton(
            onClick = { infoOpen = true },
        ) {
            Icon(
                Icons.Filled.Info,
                contentDescription = "版本介绍",
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
    if (infoOpen) {
        AlertDialog(
            onDismissRequest = { infoOpen = false },
            title = { Text(version.name) },
            text = {
                Text(
                    text = version.description.ifBlank { "暂无介绍" },
                    modifier = Modifier
                        .heightIn(max = 360.dp)
                        .verticalScroll(rememberScrollState()),
                )
            },
            confirmButton = {
                TextButton(onClick = { infoOpen = false }) {
                    Text("关闭")
                }
            },
        )
    }
}

@Composable
private fun ContinueReadingCard(
    title: String,
    onClick: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(MaterialTheme.colorScheme.primaryContainer)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 12.dp),
    ) {
        Text(
            "继续阅读",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            title,
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onPrimaryContainer,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun PageListItem(
    page: ComicPageOut,
    imageModel: Any,
    isRead: Boolean,
    isCurrent: Boolean,
    onClick: () -> Unit,
) {
    val titleColor = when {
        isCurrent -> MaterialTheme.colorScheme.primary
        isRead -> MaterialTheme.colorScheme.onSurfaceVariant
        else -> MaterialTheme.colorScheme.onSurface
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(
                if (isCurrent) {
                    MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.9f)
                } else {
                    MaterialTheme.colorScheme.surface.copy(alpha = if (isRead) 0.45f else 0.72f)
                },
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AsyncImage(
            model = imageModel,
            contentDescription = page.title,
            modifier = Modifier
                .width(72.dp)
                .height(72.dp)
                .clip(RoundedCornerShape(12.dp)),
            contentScale = ContentScale.Crop,
        )
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                page.title,
                style = MaterialTheme.typography.titleMedium,
                color = titleColor,
                fontWeight = if (isRead && !isCurrent) FontWeight.Normal else FontWeight.Medium,
            )
            if (isCurrent) {
                Text(
                    "上次读到这里",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(top = 4.dp),
                )
            } else if (isRead) {
                Text(
                    "已读",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}

@Composable
private fun CollectionListItem(
    collection: TitleCollection,
    imageModel: Any,
    isRead: Boolean,
    isCurrent: Boolean,
    onClick: () -> Unit,
) {
    val titleColor = when {
        isCurrent -> MaterialTheme.colorScheme.primary
        isRead -> MaterialTheme.colorScheme.onSurfaceVariant
        else -> MaterialTheme.colorScheme.onSurface
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(
                if (isCurrent) {
                    MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.9f)
                } else {
                    MaterialTheme.colorScheme.surface.copy(alpha = if (isRead) 0.45f else 0.72f)
                },
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AsyncImage(
            model = imageModel,
            contentDescription = collection.title,
            modifier = Modifier
                .width(72.dp)
                .height(72.dp)
                .clip(RoundedCornerShape(12.dp)),
            contentScale = ContentScale.Crop,
        )
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                collection.title,
                style = MaterialTheme.typography.titleMedium,
                color = titleColor,
                fontWeight = if (isRead && !isCurrent) FontWeight.Normal else FontWeight.Medium,
            )
            Text(
                "${collection.count} 页",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
            if (isCurrent) {
                Text(
                    "上次读到这里",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(top = 2.dp),
                )
            } else if (isRead) {
                Text(
                    "已读",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
    }
}

private const val READER_MIN_SCALE = 1f
private const val READER_MAX_SCALE = 4f
private const val READER_ZOOM_EPS = 1.01f
private const val PREVIEW_BATCH = 8
private const val READER_PREFETCH_REMAINING = 5
private val DOCKED_INPUT_RESERVE_HEIGHT = 48.dp

@Composable
private fun ZoomableReaderImage(
    imageModel: Any,
    contentDescription: String?,
    useStrip: Boolean,
    heightOverWidth: Float?,
    scale: Float,
    offset: Offset,
    transformEnabled: Boolean,
    onTransform: (scale: Float, offset: Offset) -> Unit,
    onAspect: (Float) -> Unit,
    onTap: () -> Unit,
) {
    val transformState = rememberTransformableState { zoomChange, panChange, _ ->
        val newScale = (scale * zoomChange).coerceIn(READER_MIN_SCALE, READER_MAX_SCALE)
        val newOffset = if (newScale <= READER_ZOOM_EPS) {
            Offset.Zero
        } else {
            offset + panChange
        }
        onTransform(if (newScale <= READER_ZOOM_EPS) READER_MIN_SCALE else newScale, newOffset)
    }
    val imageModifier = if (useStrip) {
        val ratio = heightOverWidth
        if (ratio != null && ratio > 0f) {
            Modifier.fillMaxWidth().aspectRatio(1f / ratio)
        } else {
            Modifier.fillMaxWidth()
        }
    } else {
        Modifier.fillMaxSize()
    }
    val scrollState = rememberScrollState()
    val allowStripScroll = useStrip && scale <= READER_ZOOM_EPS

    Box(
        modifier = Modifier
            .fillMaxSize()
            .clipToBounds()
            .then(if (allowStripScroll) Modifier.verticalScroll(scrollState) else Modifier)
            .pointerInput(Unit) {
                detectTapGestures(onTap = { onTap() })
            },
        contentAlignment = if (useStrip) Alignment.TopCenter else Alignment.Center,
    ) {
        AsyncImage(
            model = imageModel,
            contentDescription = contentDescription,
            modifier = imageModifier
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                    translationX = offset.x
                    translationY = offset.y
                }
                .transformable(
                    state = transformState,
                    canPan = { scale > READER_ZOOM_EPS },
                    enabled = transformEnabled,
                ),
            contentScale = if (useStrip) ContentScale.FillWidth else ContentScale.Fit,
            onSuccess = { state ->
                val d = state.result.drawable
                val w = d.intrinsicWidth
                val h = d.intrinsicHeight
                if (w > 0 && h > 0) {
                    onAspect(h.toFloat() / w.toFloat())
                }
            },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PageReaderScreen(
    pageId: Int,
    onBack: () -> Unit,
    onSessionExpired: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    val source = remember(pageId) { DoujinReaderSource(app, pageId) }
    PageReaderScreen(
        source = source,
        onBack = onBack,
        onSessionExpired = onSessionExpired,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PageReaderScreen(
    source: ReaderSource,
    onBack: () -> Unit,
    onSessionExpired: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    var pages by remember { mutableStateOf<List<ReaderPage>>(emptyList()) }
    var initialPageId by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(true) }
    var chromeVisible by remember { mutableStateOf(false) }
    var chromeTick by remember { mutableIntStateOf(0) }
    var commentsOpen by remember { mutableStateOf(false) }
    var dockedMode by remember { mutableStateOf(app.commentsLayout.dockedEnabled) }
    var sortTab by remember { mutableIntStateOf(0) }
    var comments by remember { mutableStateOf<List<CommentOut>>(emptyList()) }
    var commentCount by remember { mutableIntStateOf(0) }
    var commentsLoading by remember { mutableStateOf(false) }
    var draft by remember { mutableStateOf("") }
    var replyTo by remember { mutableStateOf<CommentOut?>(null) }
    var sending by remember { mutableStateOf(false) }
    var actionError by remember { mutableStateOf<String?>(null) }
    var composerOpen by remember { mutableStateOf(false) }
    var previewVisibleCount by remember { mutableIntStateOf(PREVIEW_BATCH) }
    var pagerReady by remember { mutableStateOf(false) }
    var initialLocateDone by remember { mutableStateOf(false) }
    var catalogTotal by remember { mutableIntStateOf(0) }
    var nextOffset by remember { mutableIntStateOf(0) }
    var catalogHasMore by remember { mutableStateOf(false) }
    var catalogLoadingMore by remember { mutableStateOf(false) }
    var savingImage by remember { mutableStateOf(false) }
    var usingOfflineCache by remember { mutableStateOf(false) }
    var commentsFromCache by remember { mutableStateOf(false) }
    var showVersionInfo by remember { mutableStateOf(false) }
    var versionDescription by remember { mutableStateOf("") }
    var versionInfoOpen by remember { mutableStateOf(false) }
    var readerScale by remember { mutableFloatStateOf(1f) }
    var readerOffset by remember { mutableStateOf(Offset.Zero) }
    val aspectByPageId = remember { mutableStateMapOf<Int, Float>() }
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    val pagerState = rememberPagerState(
        initialPage = 0,
        pageCount = { pages.size.coerceAtLeast(1) },
    )
    val currentPage = if (pagerReady) {
        pages.getOrNull(pagerState.settledPage)
    } else {
        pages.find { it.id == initialPageId }
    }
    val currentPageId = currentPage?.id ?: initialPageId
    val latestPageId = rememberUpdatedState(currentPageId)
    val commentsLoadJob = remember { object { var job: Job? = null } }
    val gesturesBlocked = !dockedMode && commentsOpen
    val configuration = LocalConfiguration.current
    val previewMaxHeight = (configuration.screenHeightDp * 0.2f).dp

    fun noteOfflineCache(fromCache: Boolean) {
        if (!source.supportsOffline) {
            usingOfflineCache = false
            return
        }
        if (fromCache) {
            usingOfflineCache = true
            if (!app.offlineHintShownThisProcess) {
                app.offlineHintShownThisProcess = true
                Toast.makeText(context, "留作纪念，后会有期！", Toast.LENGTH_SHORT).show()
            }
        } else {
            usingOfflineCache = false
        }
    }

    fun doSaveCurrentPage() {
        val page = currentPage ?: return
        if (savingImage) return
        chromeTick += 1
        scope.launch {
            savingImage = true
            try {
                val url = AppConfig.mediaUrl(page.imageUrl)
                val name = "p${page.pageNo}_${page.title}"
                val msg = ImageGallerySaver.saveFromUrl(context, url, name)
                Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(
                    context,
                    e.message?.takeIf { it.isNotBlank() } ?: "保存失败",
                    Toast.LENGTH_SHORT,
                ).show()
            } finally {
                savingImage = false
            }
        }
    }

    val storagePermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            doSaveCurrentPage()
        } else {
            Toast.makeText(context, "需要存储权限才能保存到相册", Toast.LENGTH_SHORT).show()
        }
    }

    fun requestSaveCurrentPage() {
        if (currentPage == null || savingImage) return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            doSaveCurrentPage()
            return
        }
        val granted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
        ) == PackageManager.PERMISSION_GRANTED
        if (granted) {
            doSaveCurrentPage()
        } else {
            storagePermissionLauncher.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }
    }

    fun bootstrapCatalog() {
        scope.launch {
            loading = true
            error = null
            pagerReady = false
            initialLocateDone = false
            pages = emptyList()
            catalogTotal = 0
            nextOffset = 0
            catalogHasMore = false
            usingOfflineCache = false
            try {
                val boot = source.bootstrap()
                pages = boot.pages
                initialPageId = boot.initialPageId
                catalogTotal = boot.catalogTotal
                nextOffset = boot.nextOffset
                catalogHasMore = boot.catalogHasMore
                showVersionInfo = boot.showVersionInfo
                versionDescription = boot.versionDescription
                noteOfflineCache(boot.fromCache)
                if (boot.pages.isEmpty()) {
                    error = "还没有漫画"
                }
                boot.switchMessage?.let { snackbar.showSnackbar(it) }
            } catch (e: Exception) {
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                    return@launch
                }
                error = userFacingError(e, "加载失败")
            } finally {
                loading = false
            }
        }
    }

    fun appendCatalog() {
        if (catalogLoadingMore || !catalogHasMore) return
        scope.launch {
            catalogLoadingMore = true
            try {
                val chunk = source.loadMoreCatalog(pages, nextOffset)
                if (chunk.fromCache) noteOfflineCache(true)
                pages = chunk.pages
                catalogTotal = chunk.catalogTotal
                nextOffset = chunk.nextOffset
                catalogHasMore = chunk.catalogHasMore
            } catch (e: Exception) {
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                }
            } finally {
                catalogLoadingMore = false
            }
        }
    }

    fun commentAnchorId(c: CommentOut?): Int? {
        if (c == null) return null
        return c.pageId ?: c.kingSlotId
    }

    fun refreshComments(forPageId: Int = currentPageId) {
        commentsLoadJob.job?.cancel()
        if (commentAnchorId(comments.firstOrNull()) != forPageId) {
            comments = emptyList()
            commentCount = 0
        }
        commentsLoading = true
        actionError = null
        commentsLoadJob.job = scope.launch {
            try {
                val sort = if (dockedMode || sortTab == 1) "hot" else "latest"
                val cached = source.listComments(forPageId, sort = sort)
                if (forPageId != latestPageId.value) return@launch
                comments = cached.items
                commentCount = cached.items.size
                commentsFromCache = cached.fromCache
                if (cached.fromCache) noteOfflineCache(true)
                if (dockedMode) {
                    previewVisibleCount = PREVIEW_BATCH
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                if (forPageId != latestPageId.value) return@launch
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                    return@launch
                }
                commentsFromCache = false
                actionError = userFacingError(e, "评论加载失败")
            } finally {
                if (forPageId == latestPageId.value) {
                    commentsLoading = false
                }
            }
        }
    }

    fun refreshCommentCount(forPageId: Int) {
        commentsLoadJob.job?.cancel()
        commentsLoadJob.job = scope.launch {
            try {
                val cached = source.listComments(forPageId, sort = "latest")
                if (forPageId != latestPageId.value) return@launch
                commentCount = cached.items.size
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                if (forPageId != latestPageId.value) return@launch
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                }
            }
        }
    }

    fun revealChrome() {
        chromeVisible = true
        chromeTick += 1
    }

    fun closeComments() {
        scope.launch {
            sheetState.hide()
            commentsOpen = false
            replyTo = null
        }
    }

    fun toggleDockedMode() {
        if (commentsOpen) {
            closeComments()
        }
        composerOpen = false
        replyTo = null
        draft = ""
        dockedMode = !dockedMode
        app.commentsLayout.dockedEnabled = dockedMode
    }

    fun closeComposer() {
        composerOpen = false
        replyTo = null
        draft = ""
    }

    fun updateCommentLike(targetId: Int, liked: Boolean, count: Int) {
        fun mapOne(c: CommentOut): CommentOut {
            val self = if (c.id == targetId) c.copy(likedByMe = liked, likeCount = count) else c
            return self.copy(
                replies = self.replies.map { r ->
                    if (r.id == targetId) r.copy(likedByMe = liked, likeCount = count) else r
                },
            )
        }
        comments = comments.map(::mapOne)
    }

    fun openComposer(target: CommentOut?) {
        if (commentsFromCache || usingOfflineCache) {
            actionError = "离线无法操作"
            return
        }
        replyTo = target
        composerOpen = true
    }

    fun onToggleCommentLike(comment: CommentOut) {
        if (commentsFromCache || usingOfflineCache) {
            actionError = "离线无法操作"
            return
        }
        scope.launch {
            try {
                if (comment.likedByMe) {
                    ApiClient.api.unlikeComment(comment.id)
                    updateCommentLike(
                        comment.id,
                        false,
                        (comment.likeCount - 1).coerceAtLeast(0),
                    )
                } else {
                    val state = ApiClient.api.likeComment(comment.id)
                    updateCommentLike(comment.id, state.liked, state.likeCount)
                }
            } catch (e: Exception) {
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                    return@launch
                }
                actionError = userFacingError(e, "点赞失败")
            }
        }
    }

    fun onSendComment() {
        val text = draft.trim()
        if (text.isEmpty() || sending) return
        if (commentsFromCache || usingOfflineCache) {
            actionError = "离线无法操作"
            return
        }
        scope.launch {
            sending = true
            actionError = null
            try {
                source.createComment(
                    currentPageId,
                    CommentCreate(content = text, parentId = replyTo?.id),
                )
                draft = ""
                replyTo = null
                if (dockedMode) composerOpen = false
                refreshComments(currentPageId)
            } catch (e: Exception) {
                if (!app.tokenStore.isLoggedIn) {
                    onSessionExpired()
                    return@launch
                }
                actionError = userFacingError(e, "发送失败")
            } finally {
                sending = false
            }
        }
    }

    LaunchedEffect(source) {
        chromeVisible = false
        commentsOpen = false
        composerOpen = false
        draft = ""
        replyTo = null
        bootstrapCatalog()
    }

    LaunchedEffect(pages, initialPageId, initialLocateDone) {
        if (initialLocateDone) return@LaunchedEffect
        if (pages.isEmpty()) return@LaunchedEffect
        val idx = pages.indexOfFirst { it.id == initialPageId }
        if (idx < 0) return@LaunchedEffect
        pagerState.scrollToPage(idx)
        pagerReady = true
        initialLocateDone = true
    }

    LaunchedEffect(pagerState.settledPage, pagerReady, pages, dockedMode) {
        if (!pagerReady || pages.isEmpty()) return@LaunchedEffect
        val settled = pages.getOrNull(pagerState.settledPage) ?: return@LaunchedEffect
        readerScale = 1f
        readerOffset = Offset.Zero
        source.markRead(settled)
        chromeVisible = false
        composerOpen = false
        if (!dockedMode && commentsOpen) {
            commentsOpen = false
            replyTo = null
            draft = ""
        } else if (dockedMode) {
            replyTo = null
            draft = ""
        }
        val remain = pages.lastIndex - pagerState.settledPage
        if (remain <= READER_PREFETCH_REMAINING) {
            appendCatalog()
        }
    }

    LaunchedEffect(currentPageId, pagerReady, pages) {
        if (!pagerReady) return@LaunchedEffect
        val page = pages.firstOrNull { it.id == currentPageId } ?: return@LaunchedEffect
        source.ensureImage(page)
    }

    LaunchedEffect(chromeTick) {
        if (!chromeVisible || commentsOpen) return@LaunchedEffect
        delay(3000)
        chromeVisible = false
    }

    LaunchedEffect(pagerReady, currentPageId, dockedMode, commentsOpen, sortTab) {
        if (!pagerReady) return@LaunchedEffect
        if (dockedMode || commentsOpen) {
            refreshComments(currentPageId)
        } else {
            refreshCommentCount(currentPageId)
        }
    }

    BackHandler(enabled = commentsOpen) {
        closeComments()
    }

    BackHandler(enabled = dockedMode && composerOpen) {
        closeComposer()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Box(
                modifier = Modifier
                    .then(
                        if (dockedMode) {
                            Modifier.weight(1f)
                        } else {
                            Modifier.fillMaxSize()
                        },
                    )
                    .fillMaxWidth()
                    .windowInsetsPadding(WindowInsets.safeDrawing),
            ) {
                when {
                    loading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                    error != null -> Text(
                        error ?: "",
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    )
                    pages.isNotEmpty() -> {
                        HorizontalPager(
                            state = pagerState,
                            modifier = Modifier.fillMaxSize(),
                            beyondBoundsPageCount = 1,
                            userScrollEnabled = !gesturesBlocked && readerScale <= READER_ZOOM_EPS,
                        ) { index ->
                            val item = pages[index]
                            val heightOverWidth = aspectByPageId[item.id]
                            val useStrip = ReaderDisplayMode.effectiveStrip(heightOverWidth)
                            val isSettledPage = index == pagerState.settledPage
                            ZoomableReaderImage(
                                imageModel = source.imageModel(item),
                                contentDescription = item.title,
                                useStrip = useStrip,
                                heightOverWidth = heightOverWidth,
                                scale = if (isSettledPage) readerScale else 1f,
                                offset = if (isSettledPage) readerOffset else Offset.Zero,
                                transformEnabled = !gesturesBlocked && isSettledPage,
                                onTransform = { s, o ->
                                    readerScale = s
                                    readerOffset = o
                                },
                                onAspect = { aspectByPageId[item.id] = it },
                                onTap = { revealChrome() },
                            )
                        }
                    }
                }
            }
            if (dockedMode) {
                CommentPreviewStrip(
                    comments = comments,
                    commentsLoading = commentsLoading,
                    visibleCount = previewVisibleCount,
                    interactionsEnabled = !commentsFromCache && !usingOfflineCache,
                    onLoadMore = {
                        if (previewVisibleCount < comments.size) {
                            previewVisibleCount = (previewVisibleCount + PREVIEW_BATCH)
                                .coerceAtMost(comments.size)
                        }
                    },
                    onToggleLike = ::onToggleCommentLike,
                    onOpenReply = { openComposer(it) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(previewMaxHeight),
                )
                Spacer(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(DOCKED_INPUT_RESERVE_HEIGHT),
                )
            }
        }

        if (dockedMode) {
            if (!composerOpen) {
                CommentEntryBar(
                    enabled = !commentsFromCache && !usingOfflineCache,
                    onOpen = { openComposer(null) },
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .zIndex(1f)
                        .fillMaxWidth()
                        .navigationBarsPadding(),
                )
            } else {
                CommentComposerBar(
                    draft = draft,
                    onDraftChange = { if (it.length <= 500) draft = it },
                    replyTo = replyTo,
                    sending = sending,
                    enabled = !commentsFromCache && !usingOfflineCache,
                    onSend = ::onSendComment,
                    onDismiss = { closeComposer() },
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .zIndex(1f)
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .imePadding(),
                )
            }
        }

        if (chromeVisible && !commentsOpen) {
            Surface(
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .fillMaxWidth()
                    .statusBarsPadding(),
                color = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
                tonalElevation = 0.dp,
            ) {
                TopAppBar(
                    title = {
                        Column {
                            Text(
                                currentPage?.title ?: "阅读",
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            val subtitle = currentPage?.subtitle
                            if (!subtitle.isNullOrBlank()) {
                                Text(
                                    subtitle,
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = Color.Transparent,
                        titleContentColor = MaterialTheme.colorScheme.onSurface,
                        navigationIconContentColor = MaterialTheme.colorScheme.onSurface,
                        actionIconContentColor = MaterialTheme.colorScheme.onSurface,
                    ),
                    navigationIcon = {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                        }
                    },
                    actions = {
                        IconButton(onClick = { toggleDockedMode() }) {
                            Icon(
                                imageVector = if (dockedMode) {
                                    Icons.Filled.Fullscreen
                                } else {
                                    Icons.Filled.ChatBubble
                                },
                                contentDescription = if (dockedMode) {
                                    "沉浸式模式"
                                } else {
                                    "评论区模式"
                                },
                                tint = if (dockedMode) {
                                    MaterialTheme.colorScheme.primary
                                } else {
                                    MaterialTheme.colorScheme.onSurface
                                },
                            )
                        }
                        if (showVersionInfo) {
                            IconButton(onClick = {
                                chromeTick += 1
                                versionInfoOpen = true
                            }) {
                                Icon(Icons.Filled.Info, contentDescription = "版本介绍")
                            }
                        }
                        IconButton(
                            onClick = { requestSaveCurrentPage() },
                            enabled = currentPage != null && !savingImage,
                        ) {
                            if (savingImage) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(22.dp),
                                    strokeWidth = 2.dp,
                                )
                            } else {
                                Icon(Icons.Filled.Download, contentDescription = "保存本页")
                            }
                        }
                    },
                )
            }
            if (!dockedMode && currentPage != null && error == null && !loading) {
                BadgedBox(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .navigationBarsPadding()
                        .padding(end = 16.dp, bottom = 20.dp),
                    badge = {
                        if (commentCount > 0) {
                            Badge(
                                containerColor = MaterialTheme.colorScheme.tertiary,
                                contentColor = MaterialTheme.colorScheme.onTertiary,
                            ) {
                                Text(commentCount.toString())
                            }
                        }
                    },
                ) {
                    FloatingActionButton(
                        onClick = {
                            commentsOpen = true
                            chromeVisible = false
                        },
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary,
                        elevation = FloatingActionButtonDefaults.elevation(
                            defaultElevation = 4.dp,
                            pressedElevation = 6.dp,
                        ),
                    ) {
                        Icon(Icons.Filled.ChatBubble, contentDescription = "评论")
                    }
                }
            }
        }

        SnackbarHost(
            hostState = snackbar,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .navigationBarsPadding()
                .padding(bottom = if (dockedMode) 72.dp else 16.dp),
        )
    }

    if (versionInfoOpen) {
        AlertDialog(
            onDismissRequest = { versionInfoOpen = false },
            title = {
                Text(currentPage?.subtitle?.takeIf { it.isNotBlank() } ?: "版本介绍")
            },
            text = {
                Text(
                    text = versionDescription.ifBlank { "暂无介绍" },
                    modifier = Modifier
                        .heightIn(max = 360.dp)
                        .verticalScroll(rememberScrollState()),
                )
            },
            confirmButton = {
                TextButton(onClick = { versionInfoOpen = false }) {
                    Text("关闭")
                }
            },
        )
    }

    if (!dockedMode && commentsOpen) {
        ModalBottomSheet(
            onDismissRequest = {
                commentsOpen = false
                replyTo = null
            },
            sheetState = sheetState,
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ) {
            CommentsPanelContent(
                showCloseButton = true,
                comments = comments,
                commentsLoading = commentsLoading,
                sortTab = sortTab,
                onSortTabChange = { sortTab = it },
                draft = draft,
                onDraftChange = { if (it.length <= 500) draft = it },
                replyTo = replyTo,
                onReplyToChange = { replyTo = it },
                sending = sending,
                actionError = actionError,
                interactionsEnabled = !commentsFromCache && !usingOfflineCache,
                onClose = { closeComments() },
                onToggleLike = ::onToggleCommentLike,
                onSend = ::onSendComment,
            )
        }
    }
}

@Composable
private fun CommentPreviewStrip(
    comments: List<CommentOut>,
    commentsLoading: Boolean,
    visibleCount: Int,
    interactionsEnabled: Boolean = true,
    onLoadMore: () -> Unit,
    onToggleLike: (CommentOut) -> Unit,
    onOpenReply: (CommentOut) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expandedTops by remember(comments.firstOrNull()?.pageId ?: comments.firstOrNull()?.kingSlotId) {
        mutableStateOf<Set<Int>>(emptySet())
    }
    var expandedBodies by remember(comments.firstOrNull()?.pageId ?: comments.firstOrNull()?.kingSlotId) {
        mutableStateOf<Set<Int>>(emptySet())
    }
    val scrollState = rememberScrollState()
    val visibleComments = comments.take(visibleCount)

    LaunchedEffect(visibleCount, comments.size) {
        if (visibleCount >= comments.size) return@LaunchedEffect
        kotlinx.coroutines.yield()
        if (scrollState.maxValue == 0) onLoadMore()
    }

    LaunchedEffect(scrollState, visibleCount, comments.size) {
        snapshotFlow {
            scrollState.maxValue > 0 && scrollState.value >= scrollState.maxValue - 24
        }.distinctUntilChanged().collect { nearEnd ->
            if (nearEnd) onLoadMore()
        }
    }

    val hairline = MaterialTheme.colorScheme.outline.copy(alpha = 0.22f)
    Column(modifier = modifier.fillMaxSize()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(hairline),
        )
        when {
            commentsLoading && comments.isEmpty() -> {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(12.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                }
            }
            comments.isEmpty() -> {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        "还没有评论",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            else -> {
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .verticalScroll(scrollState)
                        .padding(bottom = 4.dp),
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(start = 12.dp, end = 12.dp, top = 6.dp, bottom = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = "热评",
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.weight(1f),
                        )
                        Text(
                            text = "收起评论",
                            style = MaterialTheme.typography.labelMedium,
                            color = if (expandedTops.isNotEmpty() || expandedBodies.isNotEmpty()) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f)
                            },
                            modifier = Modifier.clickable(
                                enabled = expandedTops.isNotEmpty() || expandedBodies.isNotEmpty(),
                            ) {
                                expandedTops = emptySet()
                                expandedBodies = emptySet()
                            },
                        )
                    }
                    visibleComments.forEach { c ->
                        CommentPreviewRow(
                            comment = c,
                            indented = false,
                            bodyExpanded = c.id in expandedBodies,
                            interactionsEnabled = interactionsEnabled,
                            onToggleBody = {
                                expandedBodies = if (c.id in expandedBodies) {
                                    expandedBodies - c.id
                                } else {
                                    expandedBodies + c.id
                                }
                            },
                            onOpenReply = { onOpenReply(c) },
                            onToggleLike = onToggleLike,
                        )
                        val sortedReplies = sortRepliesForPreview(c.replies)
                        val expanded = c.id in expandedTops
                        if (expanded) {
                            c.replies.forEach { r ->
                                CommentPreviewRow(
                                    comment = r,
                                    indented = true,
                                    bodyExpanded = r.id in expandedBodies,
                                    interactionsEnabled = interactionsEnabled,
                                    onToggleBody = {
                                        expandedBodies = if (r.id in expandedBodies) {
                                            expandedBodies - r.id
                                        } else {
                                            expandedBodies + r.id
                                        }
                                    },
                                    onOpenReply = { onOpenReply(r) },
                                    onToggleLike = onToggleLike,
                                )
                            }
                        }
                        if (sortedReplies.isNotEmpty()) {
                            Text(
                                text = if (expanded) {
                                    "收起"
                                } else {
                                    "展开 ${sortedReplies.size} 条回复"
                                },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier
                                    .padding(start = 28.dp, end = 12.dp, top = 0.dp, bottom = 4.dp)
                                    .clickable {
                                        expandedTops = if (expanded) {
                                            expandedTops - c.id
                                        } else {
                                            expandedTops + c.id
                                        }
                                    },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CommentPreviewRow(
    comment: CommentOut,
    indented: Boolean,
    bodyExpanded: Boolean,
    interactionsEnabled: Boolean = true,
    onToggleBody: () -> Unit,
    onOpenReply: () -> Unit,
    onToggleLike: (CommentOut) -> Unit,
) {
    val avatarSize = if (indented) 24.dp else 28.dp
    val avatarUrl = comment.authorAvatarUrl.takeIf { it.isNotBlank() }?.let { AppConfig.mediaUrl(it) }
    val cardShape = RoundedCornerShape(10.dp)
    var hasOverflow by remember(comment.id, comment.content) { mutableStateOf(false) }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(
                start = if (indented) 28.dp else 12.dp,
                end = 12.dp,
                top = 3.dp,
                bottom = 3.dp,
            )
            .border(
                width = 1.dp,
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.35f),
                shape = cardShape,
            )
            .background(
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.12f),
                shape = cardShape,
            )
            .clip(cardShape)
            .clickable(enabled = interactionsEnabled, onClick = onOpenReply)
            .padding(horizontal = 8.dp, vertical = 6.dp),
    ) {
    Row(
        verticalAlignment = Alignment.Top,
    ) {
        if (avatarUrl != null) {
            AsyncImage(
                model = avatarUrl,
                contentDescription = null,
                modifier = Modifier
                    .size(avatarSize)
                    .clip(CircleShape),
                contentScale = ContentScale.Crop,
            )
        } else {
            Box(
                modifier = Modifier
                    .size(avatarSize)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = comment.authorNickname.take(1),
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
        Spacer(modifier = Modifier.width(8.dp))
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    comment.authorNickname,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    " · ${formatCommentTime(comment.createdAt)}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(start = 6.dp),
                )
            }
            val replyNick = comment.replyToNickname
            if (!replyNick.isNullOrBlank()) {
                Text(
                    "回复 $replyNick",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                comment.content,
                style = MaterialTheme.typography.bodySmall,
                maxLines = if (bodyExpanded) Int.MAX_VALUE else 2,
                overflow = TextOverflow.Ellipsis,
                onTextLayout = { layout ->
                    if (!bodyExpanded) hasOverflow = layout.hasVisualOverflow
                },
                modifier = Modifier.padding(top = 2.dp),
            )
        }
        IconButton(
            onClick = { onToggleLike(comment) },
            enabled = interactionsEnabled,
            modifier = Modifier.size(32.dp),
        ) {
            Icon(
                imageVector = if (comment.likedByMe) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder,
                contentDescription = if (comment.likedByMe) "取消赞" else "点赞",
                tint = if (comment.likedByMe) Color(0xFFE53935) else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(16.dp),
            )
        }
        Text(
            text = comment.likeCount.toString(),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
    if (hasOverflow || bodyExpanded) {
        Text(
            text = if (bodyExpanded) "收起" else "展开全文",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier
                .align(Alignment.End)
                .padding(top = 2.dp)
                .clickable(onClick = onToggleBody),
        )
    }
}
}

@Composable
private fun CommentEntryBar(
    onOpen: () -> Unit,
    enabled: Boolean = true,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(20.dp)
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 6.dp)
            .height(36.dp)
            .border(
                width = 1.dp,
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f),
                shape = shape,
            )
            .background(
                color = MaterialTheme.colorScheme.background.copy(alpha = 0.55f),
                shape = shape,
            )
            .clip(shape)
            .clickable(enabled = enabled, onClick = onOpen)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = "写留言...",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = "留言",
            style = MaterialTheme.typography.labelMedium,
            color = if (enabled) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f)
            },
        )
    }
}

@Composable
private fun CommentComposerBar(
    draft: String,
    onDraftChange: (String) -> Unit,
    replyTo: CommentOut?,
    sending: Boolean,
    enabled: Boolean = true,
    onSend: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(18.dp)
    val outline = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.background.copy(alpha = 0.94f)),
        color = Color.Transparent,
        tonalElevation = 0.dp,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .border(
                    width = 1.dp,
                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.22f),
                )
                .padding(horizontal = 12.dp, vertical = 6.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = if (replyTo != null) "回复 ${replyTo.authorNickname}" else "留言",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = "取消",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable(onClick = onDismiss),
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                val placeholder = if (replyTo != null) "写回复" else "写评论"
                BasicTextField(
                    value = draft,
                    onValueChange = onDraftChange,
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = 36.dp, max = 72.dp),
                    textStyle = MaterialTheme.typography.bodySmall.copy(
                        color = MaterialTheme.colorScheme.onSurface,
                    ),
                    cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                    maxLines = 3,
                    decorationBox = { inner ->
                        Box(
                            modifier = Modifier
                                .border(1.dp, outline, shape)
                                .background(
                                    MaterialTheme.colorScheme.background.copy(alpha = 0.55f),
                                    shape,
                                )
                                .padding(horizontal = 12.dp, vertical = 8.dp),
                            contentAlignment = Alignment.CenterStart,
                        ) {
                            if (draft.isEmpty()) {
                                Text(
                                    text = placeholder,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            inner()
                        }
                    },
                )
                Text(
                    text = if (sending) "…" else "发送",
                    style = MaterialTheme.typography.labelMedium,
                    color = if (enabled && !sending && draft.isNotBlank()) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f)
                    },
                    modifier = Modifier.clickable(
                        enabled = enabled && !sending && draft.isNotBlank(),
                        onClick = onSend,
                    ),
                )
            }
        }
    }
}

@Composable
private fun CommentsPanelContent(
    modifier: Modifier = Modifier
        .fillMaxWidth()
        .fillMaxHeight(0.9f),
    showCloseButton: Boolean,
    comments: List<CommentOut>,
    commentsLoading: Boolean,
    sortTab: Int,
    onSortTabChange: (Int) -> Unit,
    draft: String,
    onDraftChange: (String) -> Unit,
    replyTo: CommentOut?,
    onReplyToChange: (CommentOut?) -> Unit,
    sending: Boolean,
    actionError: String?,
    interactionsEnabled: Boolean = true,
    onClose: () -> Unit,
    onToggleLike: (CommentOut) -> Unit,
    onSend: () -> Unit,
) {
    var expandedTops by remember { mutableStateOf<Set<Int>>(emptySet()) }

    Column(modifier = modifier) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (showCloseButton) {
                IconButton(onClick = onClose) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "关闭评论")
                }
            }
            Text(
                "评论",
                style = MaterialTheme.typography.titleMedium,
                modifier = if (showCloseButton) {
                    Modifier.weight(1f)
                } else {
                    Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                },
            )
        }
        TabRow(
            selectedTabIndex = sortTab,
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.primary,
            indicator = { tabPositions ->
                TabRowDefaults.SecondaryIndicator(
                    modifier = Modifier.tabIndicatorOffset(tabPositions[sortTab]),
                    color = MaterialTheme.colorScheme.primary,
                )
            },
        ) {
            Tab(
                selected = sortTab == 0,
                onClick = { onSortTabChange(0) },
                text = { Text("最新") },
                selectedContentColor = MaterialTheme.colorScheme.primary,
                unselectedContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Tab(
                selected = sortTab == 1,
                onClick = { onSortTabChange(1) },
                text = { Text("最热") },
                selectedContentColor = MaterialTheme.colorScheme.primary,
                unselectedContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        actionError?.let {
            Text(
                it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
            )
        }
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
        ) {
            when {
                commentsLoading && comments.isEmpty() -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                comments.isEmpty() -> {
                    Text(
                        "还没有评论，来抢沙发吧。",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.align(Alignment.Center).padding(16.dp),
                    )
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(bottom = 8.dp),
                    ) {
                        comments.forEach { c ->
                            item(key = "c-${c.id}") {
                                CommentBlock(
                                    comment = c,
                                    indented = false,
                                    interactionsEnabled = interactionsEnabled,
                                    onReply = { onReplyToChange(c) },
                                    onToggleLike = onToggleLike,
                                )
                            }
                            val sortedReplies = sortRepliesForPreview(c.replies)
                            val expanded = c.id in expandedTops
                            val visible = when {
                                expanded -> c.replies
                                sortedReplies.size <= 1 -> sortedReplies
                                else -> listOfNotNull(sortedReplies.firstOrNull())
                            }
                            visible.forEach { r ->
                                item(key = "r-${r.id}") {
                                    CommentBlock(
                                        comment = r,
                                        indented = true,
                                        interactionsEnabled = interactionsEnabled,
                                        onReply = { onReplyToChange(r) },
                                        onToggleLike = onToggleLike,
                                    )
                                }
                            }
                            if (sortedReplies.size > 1) {
                                item(key = "fold-${c.id}") {
                                    Text(
                                        text = if (expanded) {
                                            "收起"
                                        } else {
                                            "展开 ${sortedReplies.size - 1} 条回复"
                                        },
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier
                                            .padding(start = 56.dp, end = 16.dp, top = 2.dp, bottom = 8.dp)
                                            .clickable {
                                                expandedTops = if (expanded) {
                                                    expandedTops - c.id
                                                } else {
                                                    expandedTops + c.id
                                                }
                                            },
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
        replyTo?.let {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "回复 ${it.authorNickname}",
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.secondary,
                )
                TextButton(onClick = { onReplyToChange(null) }) { Text("取消") }
            }
        }
        OutlinedTextField(
            value = draft,
            onValueChange = onDraftChange,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            enabled = interactionsEnabled,
            label = { Text("写评论") },
            minLines = 2,
            shape = MaterialTheme.shapes.medium,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MaterialTheme.colorScheme.primary,
                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                focusedLabelColor = MaterialTheme.colorScheme.primary,
                unfocusedLabelColor = MaterialTheme.colorScheme.onSurfaceVariant,
                cursorColor = MaterialTheme.colorScheme.primary,
                focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f),
            ),
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.End,
        ) {
            Button(
                onClick = onSend,
                enabled = interactionsEnabled && !sending && draft.isNotBlank(),
            ) {
                Text(if (sending) "发送中…" else "发送")
            }
        }
    }
}

private fun sortRepliesForPreview(replies: List<CommentOut>): List<CommentOut> {
    return replies.sortedWith(
        compareByDescending<CommentOut> { it.likeCount }
            .thenByDescending { it.createdAt },
    )
}

private fun formatCommentTime(raw: String): String {
    val display = DateTimeFormatter.ofPattern("MM-dd")
    return try {
        OffsetDateTime.parse(raw).format(display)
    } catch (_: Exception) {
        try {
            LocalDateTime.parse(raw.take(19)).format(display)
        } catch (_: Exception) {
            raw.take(10).let { s ->
                if (s.length >= 10 && s[4] == '-') "${s.substring(5, 7)}-${s.substring(8, 10)}" else s
            }
        }
    }
}

@Composable
private fun CommentBlock(
    comment: CommentOut,
    indented: Boolean,
    interactionsEnabled: Boolean = true,
    onReply: () -> Unit,
    onToggleLike: (CommentOut) -> Unit,
) {
    val avatarSize = if (indented) 28.dp else 36.dp
    val avatarUrl = comment.authorAvatarUrl.takeIf { it.isNotBlank() }?.let { AppConfig.mediaUrl(it) }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = if (indented) 48.dp else 16.dp, end = 12.dp, top = 10.dp, bottom = 4.dp),
    ) {
        if (avatarUrl != null) {
            AsyncImage(
                model = avatarUrl,
                contentDescription = null,
                modifier = Modifier
                    .size(avatarSize)
                    .clip(CircleShape),
                contentScale = ContentScale.Crop,
            )
        } else {
            Box(
                modifier = Modifier
                    .size(avatarSize)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = comment.authorNickname.take(1),
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
        Spacer(modifier = Modifier.width(10.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                comment.authorNickname,
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            val replyNick = comment.replyToNickname
            if (!replyNick.isNullOrBlank()) {
                Text(
                    "回复 $replyNick",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
            Text(
                comment.content,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 4.dp),
            )
            Row(
                modifier = Modifier.padding(top = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    formatCommentTime(comment.createdAt),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    " · ",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text = "回复",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (interactionsEnabled) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f)
                    },
                    modifier = Modifier.clickable(
                        enabled = interactionsEnabled,
                        onClick = onReply,
                    ),
                )
                Spacer(modifier = Modifier.weight(1f))
                IconButton(
                    onClick = { onToggleLike(comment) },
                    enabled = interactionsEnabled,
                    modifier = Modifier.size(32.dp),
                ) {
                    Icon(
                        imageVector = if (comment.likedByMe) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder,
                        contentDescription = if (comment.likedByMe) "取消赞" else "点赞",
                        tint = if (comment.likedByMe) Color(0xFFE53935) else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(18.dp),
                    )
                }
                Text(
                    text = comment.likeCount.toString(),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
