package com.owlhouse.reader.ui.notifications

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.owlhouse.reader.OwlHouseApp
import com.owlhouse.reader.config.AppConfig
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.api.NotificationOut
import com.owlhouse.reader.data.api.userFacingError
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationsScreen(
    onBack: () -> Unit,
    onOpenPage: (Int) -> Unit,
    onOpenKing: (versionId: Int, slotId: Int) -> Unit,
    onGoHome: () -> Unit,
    onSessionExpired: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<NotificationOut>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    fun load() {
        scope.launch {
            loading = true
            error = null
            try {
                items = ApiClient.api.listNotifications().items
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

    LaunchedEffect(Unit) { load() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text("消息") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                    titleContentColor = MaterialTheme.colorScheme.onBackground,
                    navigationIconContentColor = MaterialTheme.colorScheme.onBackground,
                    actionIconContentColor = MaterialTheme.colorScheme.secondary,
                ),
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    TextButton(
                        onClick = {
                            scope.launch {
                                try {
                                    ApiClient.api.markAllNotificationsRead()
                                    load()
                                } catch (e: Exception) {
                                    if (!app.tokenStore.isLoggedIn) {
                                        onSessionExpired()
                                        return@launch
                                    }
                                    error = userFacingError(e, "操作失败")
                                }
                            }
                        },
                        enabled = items.any { !it.isRead },
                    ) {
                        Text("全部已读")
                    }
                },
            )
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            when {
                loading && items.isEmpty() -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                error != null && items.isEmpty() -> {
                    Text(
                        text = error ?: "",
                        modifier = Modifier.align(Alignment.Center),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
                items.isEmpty() -> {
                    Text(
                        text = "暂无消息",
                        modifier = Modifier.align(Alignment.Center),
                        style = MaterialTheme.typography.bodyLarge,
                    )
                }
                else -> {
                    LazyColumn(
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        items(items, key = { it.id }) { n ->
                            NotificationRow(
                                item = n,
                                onClick = {
                                    scope.launch {
                                        try {
                                            if (!n.isRead) {
                                                ApiClient.api.markNotificationRead(n.id)
                                            }
                                            val kingSlotId = n.kingSlotId
                                            if (kingSlotId != null && kingSlotId > 0) {
                                                val preferred = app.kingProgress.lastVersionId
                                                    .takeIf { it > 0 }
                                                val resolved = ApiClient.api.resolveKingPage(
                                                    slotId = kingSlotId,
                                                    preferredVersionId = preferred,
                                                )
                                                onOpenKing(resolved.versionId, resolved.slotId)
                                            } else {
                                                val pageId = n.pageId
                                                if (pageId != null && pageId > 0) {
                                                    onOpenPage(pageId)
                                                } else {
                                                    onGoHome()
                                                }
                                            }
                                        } catch (e: Exception) {
                                            if (!app.tokenStore.isLoggedIn) {
                                                onSessionExpired()
                                                return@launch
                                            }
                                            error = userFacingError(e, "操作失败")
                                        }
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
private fun NotificationRow(
    item: NotificationOut,
    onClick: () -> Unit,
) {
    val avatarUrl = if (item.actorAvatarUrl.isNotBlank()) {
        AppConfig.mediaUrl(item.actorAvatarUrl)
    } else {
        null
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(
                if (item.isRead) {
                    MaterialTheme.colorScheme.surface.copy(alpha = 0.45f)
                } else {
                    MaterialTheme.colorScheme.surface.copy(alpha = 0.85f)
                },
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.Top,
    ) {
        if (avatarUrl != null) {
            AsyncImage(
                model = avatarUrl,
                contentDescription = null,
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape),
                contentScale = ContentScale.Crop,
            )
        } else {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = item.actorNickname.take(1),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = item.summary,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = if (item.isRead) FontWeight.Normal else FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
            )
            if (item.commentPreview.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = item.commentPreview,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        if (!item.isRead) {
            Text(
                text = "未读",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.tertiary,
            )
        }
    }
}
