package com.owlhouse.reader.data

import android.content.Context

/** 首页「合集模式」开关：同人与长寿之王各存一份（默认都开）。 */
class CollectionModeStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** 同人合集模式。兼容旧键 collection_mode。 */
    var doujinEnabled: Boolean
        get() = prefs.getBoolean(KEY_DOUJIN, prefs.getBoolean(KEY_LEGACY, true))
        set(value) {
            prefs.edit()
                .putBoolean(KEY_DOUJIN, value)
                .putBoolean(KEY_LEGACY, value)
                .apply()
        }

    /** 长寿之王合集模式。 */
    var kingEnabled: Boolean
        get() = prefs.getBoolean(KEY_KING, true)
        set(value) {
            prefs.edit().putBoolean(KEY_KING, value).apply()
        }

    @Deprecated("Use doujinEnabled", ReplaceWith("doujinEnabled"))
    var enabled: Boolean
        get() = doujinEnabled
        set(value) {
            doujinEnabled = value
        }

    companion object {
        private const val PREFS = "owlhouse_collection"
        private const val KEY_LEGACY = "collection_mode"
        private const val KEY_DOUJIN = "doujin_collection_mode"
        private const val KEY_KING = "king_collection_mode"
    }
}
