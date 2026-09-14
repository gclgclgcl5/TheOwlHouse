package com.owlhouse.reader.data

import android.content.Context

/** 阅读页「评论区模式」开关（默认开，评论区常驻底部）。 */
class ReaderCommentsLayoutStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var dockedEnabled: Boolean
        get() = prefs.getBoolean(KEY_DOCKED, true)
        set(value) {
            prefs.edit().putBoolean(KEY_DOCKED, value).apply()
        }

    companion object {
        private const val PREFS = "owlhouse_comments_layout"
        private const val KEY_DOCKED = "docked_enabled"
    }
}
