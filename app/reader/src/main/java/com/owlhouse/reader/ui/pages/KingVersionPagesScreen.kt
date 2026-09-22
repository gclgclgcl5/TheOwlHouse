package com.owlhouse.reader.ui.pages

import android.widget.Toast
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
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import coil.compose.AsyncImage
import com.owlhouse.reader.OwlHouseApp
import com.owlhouse.reader.config.AppConfig
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.api.KingPageOut
import com.owlhouse.reader.data.api.userFacingError

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun KingVersionPagesScreen(
    versionId: Int,
    onBack: () -> Unit,
    onOpenSlot: (slotId: Int) -> Unit,
    onSessionExpired: () -> Unit,
) {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var versionName by remember { mutableStateOf("") }
    var items by remember { mutableStateOf<List<KingPageOut>>(emptyList()) }
    var lastPageNo by remember { mutableIntStateOf(app.kingProgress.lastPageNo) }

    fun tipMissing() {
        Toast.makeText(context, "本版本该页尚未更新", Toast.LENGTH_SHORT).show()
    }

    fun openItem(page: KingPageOut) {
        if (page.imageUrl.isBlank()) {
            tipMissing()
            return
        }
        onOpenSlot(page.slotId)
    }

    LaunchedEffect(versionId) {
        loading = true
        error = null
        try {
            val res = ApiClient.api.listKingVersionPages(versionId, includeMissing = true)
            versionName = res.versionName
            items = res.items
            lastPageNo = app.kingProgress.lastPageNo
        } catch (e: Exception) {
            if (!app.tokenStore.isLoggedIn) {
                onSessionExpired()
                return@LaunchedEffect
            }
            error = userFacingError(e, "加载失败")
        } finally {
            loading = false
        }
    }

    val continuePage = remember(items, lastPageNo) {
        if (lastPageNo > 0) items.firstOrNull { it.pageNo == lastPageNo } else null
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding(),
    ) {
        TopAppBar(
            title = {
                Text(
                    text = versionName.ifBlank { "长寿之王" },
                    maxLines = 1,
                )
            },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.background,
                titleContentColor = MaterialTheme.colorScheme.onBackground,
                navigationIconContentColor = MaterialTheme.colorScheme.onBackground,
            ),
        )

        when {
            loading -> Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator()
            }
            error != null && items.isEmpty() -> Box(
                modifier = Modifier.fillMaxSize().padding(24.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(error ?: "", color = MaterialTheme.colorScheme.error)
            }
            items.isEmpty() -> Box(
                modifier = Modifier.fillMaxSize().padding(24.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text("该版本还没有页。")
            }
            else -> LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.fillMaxSize(),
            ) {
                if (continuePage != null) {
                    item(key = "continue-reading") {
                        ContinueReadingCardLike(
                            title = continuePage.title.ifBlank {
                                app.kingProgress.lastTitle.ifBlank { "第 ${continuePage.pageNo} 页" }
                            },
                            onClick = { openItem(continuePage) },
                        )
                    }
                }
                items(items, key = { it.slotId }) { page ->
                    val missing = page.imageUrl.isBlank()
                    val isCurrent = lastPageNo > 0 && page.pageNo == lastPageNo
                    val isRead = app.kingProgress.isRead(page.pageNo)
                    KingBrowsePageRow(
                        page = page,
                        missing = missing,
                        isRead = isRead,
                        isCurrent = isCurrent,
                        onClick = { openItem(page) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ContinueReadingCardLike(
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
private fun KingBrowsePageRow(
    page: KingPageOut,
    missing: Boolean,
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
        if (missing) {
            Box(
                modifier = Modifier
                    .width(72.dp)
                    .height(72.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "未更新",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontWeight = FontWeight.SemiBold,
                    textAlign = TextAlign.Center,
                )
            }
        } else {
            AsyncImage(
                model = AppConfig.mediaUrl(page.imageUrl),
                contentDescription = page.title,
                modifier = Modifier
                    .width(72.dp)
                    .height(72.dp)
                    .clip(RoundedCornerShape(12.dp)),
                contentScale = ContentScale.Crop,
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                page.title.ifBlank { "第 ${page.pageNo} 页" },
                style = MaterialTheme.typography.titleMedium,
                color = titleColor,
                fontWeight = if (isRead && !isCurrent) FontWeight.Normal else FontWeight.Medium,
            )
            val sub = when {
                isCurrent -> "上次读到这里"
                isRead -> "已读"
                missing -> "未更新"
                else -> null
            }
            if (sub != null) {
                Text(
                    sub,
                    style = MaterialTheme.typography.labelSmall,
                    color = if (isCurrent) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}
