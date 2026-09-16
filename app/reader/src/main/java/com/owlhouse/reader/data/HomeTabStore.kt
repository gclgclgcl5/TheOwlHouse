package com.owlhouse.reader.data

import android.content.Context

/** 首页 Tab：doujin | king（默认 doujin）。 */
class HomeTabStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var tab: String
        get() {
            val raw = prefs.getString(KEY_TAB, TAB_DOUJIN).orEmpty()
            return if (raw == TAB_KING) TAB_KING else TAB_DOUJIN
        }
        set(value) {
            prefs.edit().putString(KEY_TAB, if (value == TAB_KING) TAB_KING else TAB_DOUJIN).apply()
        }

    val isKing: Boolean get() = tab == TAB_KING

    companion object {
        const val TAB_DOUJIN = "doujin"
        const val TAB_KING = "king"
        private const val PREFS = "owlhouse_home_tab"
        private const val KEY_TAB = "tab"
    }
}
