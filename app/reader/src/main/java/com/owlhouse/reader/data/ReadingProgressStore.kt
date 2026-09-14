package com.owlhouse.reader.data

import android.content.Context
import com.owlhouse.reader.data.api.ComicPageOut

/**
 * 本机阅读进度（不跟账号、不同步服务端）。
 * lastPage* 表示「继续阅读」落点；lastPageNo 作为已读前沿（page_no <= 该值视为已读）。
 */
class ReadingProgressStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var lastPageId: Int
        get() = prefs.getInt(KEY_PAGE_ID, 0)
        set(value) {
            prefs.edit().putInt(KEY_PAGE_ID, value).apply()
        }

    var lastPageNo: Int
        get() = prefs.getInt(KEY_PAGE_NO, 0)
        set(value) {
            prefs.edit().putInt(KEY_PAGE_NO, value).apply()
        }

    var lastTitle: String
        get() = prefs.getString(KEY_TITLE, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_TITLE, value).apply()
        }

    val hasProgress: Boolean
        get() = lastPageId > 0

    fun markRead(page: ComicPageOut) {
        val edit = prefs.edit()
            .putInt(KEY_PAGE_ID, page.id)
            .putString(KEY_TITLE, page.title)
        val no = page.pageNo
        if (no >= lastPageNo) {
            edit.putInt(KEY_PAGE_NO, no)
        }
        edit.apply()
    }

    fun isRead(page: ComicPageOut): Boolean {
        val frontier = lastPageNo
        return frontier > 0 && page.pageNo <= frontier
    }

    companion object {
        private const val PREFS = "owlhouse_reading"
        private const val KEY_PAGE_ID = "last_page_id"
        private const val KEY_PAGE_NO = "last_page_no"
        private const val KEY_TITLE = "last_title"
    }
}
