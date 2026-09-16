package com.owlhouse.reader.data

import android.content.Context

/**
 * 长寿之王整部阅读进度（本机、不跟账号）。
 * lastPageNo 为作品级已读前沿；lastVersionId 为最近阅读版本。
 */
class KingProgressStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var lastSlotId: Int
        get() = prefs.getInt(KEY_SLOT_ID, 0)
        set(value) {
            prefs.edit().putInt(KEY_SLOT_ID, value).apply()
        }

    var lastPageNo: Int
        get() = prefs.getInt(KEY_PAGE_NO, 0)
        set(value) {
            prefs.edit().putInt(KEY_PAGE_NO, value).apply()
        }

    var lastVersionId: Int
        get() = prefs.getInt(KEY_VERSION_ID, 0)
        set(value) {
            prefs.edit().putInt(KEY_VERSION_ID, value).apply()
        }

    var lastTitle: String
        get() = prefs.getString(KEY_TITLE, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_TITLE, value).apply()
        }

    fun markRead(slotId: Int, pageNo: Int, title: String, versionId: Int) {
        val edit = prefs.edit()
            .putInt(KEY_SLOT_ID, slotId)
            .putString(KEY_TITLE, title)
            .putInt(KEY_VERSION_ID, versionId)
        if (pageNo >= lastPageNo) {
            edit.putInt(KEY_PAGE_NO, pageNo)
        }
        edit.apply()
    }

    fun isRead(pageNo: Int): Boolean {
        val frontier = lastPageNo
        return frontier > 0 && pageNo <= frontier
    }

    companion object {
        private const val PREFS = "owlhouse_king_progress"
        private const val KEY_SLOT_ID = "last_slot_id"
        private const val KEY_PAGE_NO = "last_page_no"
        private const val KEY_VERSION_ID = "last_version_id"
        private const val KEY_TITLE = "last_title"
    }
}
