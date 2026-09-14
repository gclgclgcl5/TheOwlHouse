package com.owlhouse.reader.data

import android.content.Context

/** 首页「合集模式」开关（默认开）。 */
class CollectionModeStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var enabled: Boolean
        get() = prefs.getBoolean(KEY_ENABLED, true)
        set(value) {
            prefs.edit().putBoolean(KEY_ENABLED, value).apply()
        }

    companion object {
        private const val PREFS = "owlhouse_collection"
        private const val KEY_ENABLED = "collection_mode"
    }
}
