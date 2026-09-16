package com.owlhouse.reader

import android.app.Application
import android.os.Build
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.decode.GifDecoder
import coil.decode.ImageDecoderDecoder
import com.owlhouse.reader.data.CollectionModeStore
import com.owlhouse.reader.data.HomeAnnouncementStore
import com.owlhouse.reader.data.HomeTabStore
import com.owlhouse.reader.data.KingProgressStore
import com.owlhouse.reader.data.ReaderCommentsLayoutStore
import com.owlhouse.reader.data.ReadingProgressStore
import com.owlhouse.reader.data.TokenStore
import com.owlhouse.reader.data.UpdatePrefs
import com.owlhouse.reader.data.api.ApiClient
import com.owlhouse.reader.data.offline.OfflineRepository

class OwlHouseApp : Application(), ImageLoaderFactory {
    lateinit var tokenStore: TokenStore
        private set
    lateinit var readingProgress: ReadingProgressStore
        private set
    lateinit var kingProgress: KingProgressStore
        private set
    lateinit var homeTab: HomeTabStore
        private set
    lateinit var updatePrefs: UpdatePrefs
        private set
    lateinit var homeAnnouncement: HomeAnnouncementStore
        private set
    lateinit var collectionMode: CollectionModeStore
        private set
    lateinit var commentsLayout: ReaderCommentsLayoutStore
        private set
    lateinit var offline: OfflineRepository
        private set
    /** 每次冷启动仅检查一次更新，避免同一会话频繁弹窗。 */
    var updateCheckedThisLaunch: Boolean = false

    /** 本进程内离线缓存 Toast 只提示一次（首页/阅读器共用）。 */
    var offlineHintShownThisProcess: Boolean = false

    override fun onCreate() {
        super.onCreate()
        tokenStore = TokenStore(this)
        readingProgress = ReadingProgressStore(this)
        kingProgress = KingProgressStore(this)
        homeTab = HomeTabStore(this)
        updatePrefs = UpdatePrefs(this)
        homeAnnouncement = HomeAnnouncementStore(this)
        collectionMode = CollectionModeStore(this)
        commentsLayout = ReaderCommentsLayoutStore(this)
        offline = OfflineRepository(this)
        ApiClient.init(tokenStore)
    }

    override fun newImageLoader(): ImageLoader {
        return ImageLoader.Builder(this)
            .components {
                if (Build.VERSION.SDK_INT >= 28) {
                    add(ImageDecoderDecoder.Factory())
                } else {
                    add(GifDecoder.Factory())
                }
            }
            .build()
    }
}
