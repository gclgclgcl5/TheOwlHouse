package com.owlhouse.reader.data

import android.content.Context

/** 上次成功拉取的首页公告（避免切页时闪回默认文案）。 */
class HomeAnnouncementStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var title: String
        get() = prefs.getString(KEY_TITLE, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_TITLE, value).apply()
        }

    val displayedTitle: String
        get() = title.ifBlank { DEFAULT_TITLE }

    companion object {
        private const val PREFS = "owlhouse_home"
        private const val KEY_TITLE = "announcement_title"
        const val DEFAULT_TITLE = "欢迎来到沸腾群岛！"
    }
}
