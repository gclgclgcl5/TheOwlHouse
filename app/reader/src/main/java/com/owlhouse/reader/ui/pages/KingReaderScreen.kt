@file:OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)

package com.owlhouse.reader.ui.pages

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChatBubble
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.FloatingActionButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.zIndex
import coil.compose.AsyncImage
import com.owlhouse.reader.OwlHouseApp
import com.owlhouse.reader.config.AppConfig
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.api.CommentCreate
import com.owlhouse.reader.data.api.CommentOut
import com.owlhouse.reader.data.api.KingPageOut
import com.owlhouse.reader.data.api.userFacingError
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun KingReaderScreen(
    versionId: Int,
    slotId: Int,
    onBack: () -> Unit,
    onSessionExpired: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }

    var pages by remember { mutableStateOf<List<KingPageOut>>(emptyList()) }
    var activeVersionId by remember { mutableIntStateOf(versionId) }
    var versionName by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var chromeVisible by remember { mutableStateOf(true) }
    var commentsOpen by remember { mutableStateOf(false) }
    var dockedMode by remember { mutableStateOf(app.commentsLayout.dockedEnabled) }
    var sortTab by remember { mutableIntStateOf(0) }
    var comments by remember { mutableStateOf<List<CommentOut>>(emptyList()) }
    var draft by remember { mutableStateOf("") }
    var replyTo by remember { mutableStateOf<CommentOut?>(null) }
    var sending by remember { mutableStateOf(false) }
    var actionError by remember { mutableStateOf<String?>(null) }
    var initialIndex by remember { mutableIntStateOf(0) }
    var pagerReady by remember { mutableStateOf(false) }

    val pagerState = rememberPagerState(
        initialPage = 0,
        pageCount = { pages.size.coerceAtLeast(1) },
    )
    val currentPage = if (pagerReady) {
        pages.getOrNull(pagerState.settledPage)
    } else {
        pages.getOrNull(initialIndex)
    }
    val currentSlotId = currentPage?.slotId ?: 0
    val latestSlotId = rememberUpdatedState(currentSlotId)
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    fun markCurrent() {
        val p = currentPage ?: return
        app.kingProgress.markRead(
            slotId = p.slotId,
            pageNo = p.pageNo,
            title = p.title,
            versionId = activeVersionId,
        )
    }

    suspend fun refreshComments(forSlotId: Int) {
        if (forSlotId <= 0) return
        try {
            val sort = if (sortTab == 0) "latest" else "hot"
            comments = ApiClient.api.listKingComments(forSlotId, sort = sort).items
            actionError = null
        } catch (e: Exception) {
            if (!app.tokenStore.isLoggedIn) {
                onSessionExpired()
                return
            }
            actionError = userFacingError(e, "评论加载失败")
        }
    }

    fun bootstrap() {
        scope.launch {
            loading = true
            error = null
            pagerReady = false
            try {
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
                if (resolved.switched) {
                    snackbar.showSnackbar("已切换到「${resolved.versionName}」")
                }
                app.kingProgress.markRead(
                    slotId = resolved.slotId,
                    pageNo = resolved.pageNo,
                    title = resolved.title,
                    versionId = resolved.versionId,
                )
                val list = ApiClient.api.listKingVersionPages(resolved.versionId)
                pages = list.items
                versionName = list.versionName.ifBlank { resolved.versionName }
                val idx = pages.indexOfFirst { it.slotId == resolved.slotId }.coerceAtLeast(0)
                initialIndex = idx
                if (pages.isEmpty()) {
                    error = "该版本还没有已上传的页"
                }
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

    LaunchedEffect(versionId, slotId) {
        bootstrap()
    }

    LaunchedEffect(pages, initialIndex, loading) {
        if (loading || pages.isEmpty()) return@LaunchedEffect
        pagerState.scrollToPage(initialIndex.coerceIn(0, pages.lastIndex))
        pagerReady = true
        markCurrent()
        refreshComments(pages[initialIndex.coerceIn(0, pages.lastIndex)].slotId)
    }

    LaunchedEffect(pagerState, pages) {
        snapshotFlow { pagerState.settledPage }
            .distinctUntilChanged()
            .collect { page ->
                if (!pagerReady || pages.isEmpty()) return@collect
                val p = pages.getOrNull(page) ?: return@collect
                app.kingProgress.markRead(
                    slotId = p.slotId,
                    pageNo = p.pageNo,
                    title = p.title,
                    versionId = activeVersionId,
                )
                refreshComments(p.slotId)
            }
    }

    LaunchedEffect(sortTab, currentSlotId) {
        if (currentSlotId > 0) refreshComments(currentSlotId)
    }

    Scaffold(
        containerColor = Color.Black,
        snackbarHost = { SnackbarHost(snackbar) },
        floatingActionButton = {
            if (!dockedMode && pages.isNotEmpty()) {
                FloatingActionButton(
                    onClick = { commentsOpen = true },
                    containerColor = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                    elevation = FloatingActionButtonDefaults.elevation(0.dp),
                ) {
                    BadgedBox(
                        badge = {
                            if (comments.isNotEmpty()) {
                                Badge { Text(comments.size.coerceAtMost(99).toString()) }
                            }
                        },
                    ) {
                        Icon(Icons.Filled.ChatBubble, contentDescription = "评论")
                    }
                }
            }
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            when {
                loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                error != null -> Box(
                    Modifier.fillMaxSize().padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(error ?: "", color = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.height(12.dp))
                        TextButton(onClick = onBack) { Text("返回") }
                    }
                }
                pages.isEmpty() -> Box(
                    Modifier.fillMaxSize().padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("该版本还没有已上传的页", color = Color.White)
                }
                else -> {
                    HorizontalPager(
                        state = pagerState,
                        modifier = Modifier
                            .fillMaxSize()
                            .pointerInput(Unit) {
                                detectTapGestures(
                                    onTap = { chromeVisible = !chromeVisible },
                                )
                            },
                    ) { page ->
                        val item = pages[page]
                        AsyncImage(
                            model = AppConfig.mediaUrl(item.imageUrl),
                            contentDescription = item.title,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Fit,
                        )
                    }

                    if (chromeVisible) {
                        Surface(
                            color = Color.Black.copy(alpha = 0.55f),
                            modifier = Modifier
                                .fillMaxWidth()
                                .align(Alignment.TopCenter)
                                .statusBarsPadding()
                                .zIndex(2f),
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(56.dp)
                                    .padding(horizontal = 4.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                IconButton(onClick = onBack) {
                                    Icon(
                                        Icons.AutoMirrored.Filled.ArrowBack,
                                        contentDescription = "返回",
                                        tint = Color.White,
                                    )
                                }
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = currentPage?.title.orEmpty(),
                                        color = Color.White,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        fontWeight = FontWeight.SemiBold,
                                    )
                                    Text(
                                        text = versionName,
                                        color = Color.White.copy(alpha = 0.75f),
                                        style = MaterialTheme.typography.labelMedium,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                }
                                TextButton(
                                    onClick = {
                                        dockedMode = !dockedMode
                                        app.commentsLayout.dockedEnabled = dockedMode
                                        if (dockedMode) commentsOpen = false
                                    },
                                ) {
                                    Text(
                                        if (dockedMode) "沉浸" else "评论区",
                                        color = Color.White,
                                    )
                                }
                            }
                        }
                    }

                    if (dockedMode) {
                        Column(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .fillMaxWidth()
                                .background(Color.Black.copy(alpha = 0.72f))
                                .navigationBarsPadding()
                                .imePadding()
                                .zIndex(2f),
                        ) {
                            KingDockedComments(
                                comments = comments,
                                replyTo = replyTo,
                                draft = draft,
                                sending = sending,
                                actionError = actionError,
                                onDraftChange = { draft = it },
                                onReplyToChange = { replyTo = it },
                                onSend = {
                                    val p = currentPage ?: return@KingDockedComments
                                    val text = draft.trim()
                                    if (text.isEmpty() || sending) return@KingDockedComments
                                    scope.launch {
                                        sending = true
                                        try {
                                            ApiClient.api.createKingComment(
                                                p.slotId,
                                                CommentCreate(text, replyTo?.id),
                                            )
                                            draft = ""
                                            replyTo = null
                                            refreshComments(latestSlotId.value)
                                        } catch (e: Exception) {
                                            if (!app.tokenStore.isLoggedIn) onSessionExpired()
                                            else actionError = userFacingError(e, "发送失败")
                                        } finally {
                                            sending = false
                                        }
                                    }
                                },
                                onOpenAll = { commentsOpen = true },
                            )
                        }
                    }
                }
            }
        }
    }

    if (commentsOpen) {
        ModalBottomSheet(
            onDismissRequest = { commentsOpen = false },
            sheetState = sheetState,
            containerColor = MaterialTheme.colorScheme.surface,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding()
                    .imePadding()
                    .padding(bottom = 16.dp),
            ) {
                TabRow(selectedTabIndex = sortTab) {
                    Tab(selected = sortTab == 0, onClick = { sortTab = 0 }, text = { Text("最新") })
                    Tab(selected = sortTab == 1, onClick = { sortTab = 1 }, text = { Text("最热") })
                }
                if (actionError != null) {
                    Text(
                        actionError ?: "",
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                    )
                }
                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(360.dp)
                        .padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    if (comments.isEmpty()) {
                        item { Text("还没有评论，来抢沙发吧。") }
                    } else {
                        items(comments, key = { it.id }) { c ->
                            KingCommentBlock(
                                comment = c,
                                onReply = { replyTo = it },
                                onToggleLike = { comment ->
                                    scope.launch {
                                        try {
                                            if (comment.likedByMe) {
                                                ApiClient.api.unlikeComment(comment.id)
                                                comments = comments.mapLike(comment.id, false, (comment.likeCount - 1).coerceAtLeast(0))
                                            } else {
                                                val res = ApiClient.api.likeComment(comment.id)
                                                comments = comments.mapLike(comment.id, true, res.likeCount)
                                            }
                                        } catch (e: Exception) {
                                            if (!app.tokenStore.isLoggedIn) onSessionExpired()
                                        }
                                    }
                                },
                            )
                        }
                    }
                }
                if (replyTo != null) {
                    Row(
                        modifier = Modifier.padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            "回复 ${replyTo?.authorNickname}",
                            modifier = Modifier.weight(1f),
                            style = MaterialTheme.typography.bodySmall,
                        )
                        TextButton(onClick = { replyTo = null }) { Text("取消") }
                    }
                }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = draft,
                        onValueChange = { draft = it.take(500) },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("写评论") },
                        maxLines = 3,
                    )
                    TextButton(
                        enabled = !sending && draft.isNotBlank(),
                        onClick = {
                            val p = currentPage ?: return@TextButton
                            val text = draft.trim()
                            scope.launch {
                                sending = true
                                try {
                                    ApiClient.api.createKingComment(
                                        p.slotId,
                                        CommentCreate(text, replyTo?.id),
                                    )
                                    draft = ""
                                    replyTo = null
                                    refreshComments(latestSlotId.value)
                                } catch (e: Exception) {
                                    if (!app.tokenStore.isLoggedIn) onSessionExpired()
                                    else actionError = userFacingError(e, "发送失败")
                                } finally {
                                    sending = false
                                }
                            }
                        },
                    ) {
                        Text(if (sending) "…" else "发送")
                    }
                }
            }
        }
    }
}

@Composable
private fun KingDockedComments(
    comments: List<CommentOut>,
    replyTo: CommentOut?,
    draft: String,
    sending: Boolean,
    actionError: String?,
    onDraftChange: (String) -> Unit,
    onReplyToChange: (CommentOut?) -> Unit,
    onSend: () -> Unit,
    onOpenAll: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth().padding(12.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("热评", fontWeight = FontWeight.SemiBold, color = Color.White)
            Spacer(modifier = Modifier.weight(1f))
            TextButton(onClick = onOpenAll) { Text("全部") }
        }
        if (comments.isEmpty()) {
            Text("还没有评论", color = Color.White.copy(alpha = 0.7f))
        } else {
            comments.take(3).forEach { c ->
                Text(
                    "${c.authorNickname}: ${c.content}",
                    color = Color.White,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onReplyToChange(c) }
                        .padding(vertical = 4.dp),
                )
            }
        }
        if (actionError != null) {
            Text(actionError, color = MaterialTheme.colorScheme.error)
        }
        if (replyTo != null) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("回复 ${replyTo.authorNickname}", color = Color.White.copy(alpha = 0.8f), modifier = Modifier.weight(1f))
                TextButton(onClick = { onReplyToChange(null) }) { Text("取消") }
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = draft,
                onValueChange = { onDraftChange(it.take(500)) },
                modifier = Modifier.weight(1f),
                placeholder = { Text("写评论") },
                maxLines = 2,
            )
            TextButton(enabled = !sending && draft.isNotBlank(), onClick = onSend) {
                Text(if (sending) "…" else "发送")
            }
        }
    }
}

@Composable
private fun KingCommentBlock(
    comment: CommentOut,
    onReply: (CommentOut) -> Unit,
    onToggleLike: (CommentOut) -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(comment.authorNickname, fontWeight = FontWeight.SemiBold)
        Text(comment.content)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            TextButton(onClick = { onReply(comment) }) { Text("回复") }
            TextButton(onClick = { onToggleLike(comment) }) {
                Text(if (comment.likedByMe) "♥ ${comment.likeCount}" else "♡ ${comment.likeCount}")
            }
        }
        comment.replies.forEach { r ->
            Column(modifier = Modifier.padding(start = 16.dp, top = 6.dp)) {
                Text(r.authorNickname, fontWeight = FontWeight.SemiBold)
                if (!r.replyToNickname.isNullOrBlank()) {
                    Text("回复 ${r.replyToNickname}", style = MaterialTheme.typography.labelSmall)
                }
                Text(r.content)
                TextButton(onClick = { onToggleLike(r) }) {
                    Text(if (r.likedByMe) "♥ ${r.likeCount}" else "♡ ${r.likeCount}")
                }
            }
        }
    }
}

private fun List<CommentOut>.mapLike(targetId: Int, liked: Boolean, count: Int): List<CommentOut> {
    fun mapOne(c: CommentOut): CommentOut {
        val self = if (c.id == targetId) c.copy(likedByMe = liked, likeCount = count) else c
        return self.copy(
            replies = self.replies.map { r ->
                if (r.id == targetId) r.copy(likedByMe = liked, likeCount = count) else r
            },
        )
    }
    return map(::mapOne)
}
