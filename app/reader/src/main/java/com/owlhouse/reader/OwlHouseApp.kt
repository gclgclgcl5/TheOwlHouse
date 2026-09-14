package com.owlhouse.reader

import android.app.Application
import android.os.Build
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.decode.GifDecoder
import coil.decode.ImageDecoderDecoder
import com.owlhouse.reader.data.CollectionModeStore
import com.owlhouse.reader.data.HomeAnnouncementStore
import com.owlhouse.reader.data.ReaderCommentsLayoutStore
import com.owlhouse.reader.data.ReadingProgressStore
import com.owlhouse.reader.data.TokenStore
import com.owlhouse.reader.data.UpdatePrefs
import com.owlhouse.reader.data.api.ApiClient

class OwlHouseApp : Application(), ImageLoaderFactory {
    lateinit var tokenStore: TokenStore
        private set
    lateinit var readingProgress: ReadingProgressStore
        private set
    lateinit var updatePrefs: UpdatePrefs
        private set
    lateinit var homeAnnouncement: HomeAnnouncementStore
        private set
    lateinit var collectionMode: CollectionModeStore
        private set
    lateinit var commentsLayout: ReaderCommentsLayoutStore
        private set
    /** 每次冷启动仅检查一次更新，避免同一会话频繁弹窗。 */
    var updateCheckedThisLaunch: Boolean = false

    override fun onCreate() {
        super.onCreate()
        tokenStore = TokenStore(this)
        readingProgress = ReadingProgressStore(this)
        updatePrefs = UpdatePrefs(this)
        homeAnnouncement = HomeAnnouncementStore(this)
        collectionMode = CollectionModeStore(this)
        commentsLayout = ReaderCommentsLayoutStore(this)
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
