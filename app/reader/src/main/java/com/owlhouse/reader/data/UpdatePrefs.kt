package com.owlhouse.reader.data

import android.content.Context

/** 记录更新提醒的忽略/冷却状态。 */
class UpdatePrefs(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var ignoredVersionCode: Int
        get() = prefs.getInt(KEY_IGNORED, 0)
        set(value) {
            prefs.edit().putInt(KEY_IGNORED, value).apply()
        }

    /** 「稍后提醒」对应的冷却截止时间（毫秒时间戳）。 */
    var snoozeUntilMs: Long
        get() = prefs.getLong(KEY_SNOOZE_UNTIL_MS, 0L)
        set(value) {
            prefs.edit().putLong(KEY_SNOOZE_UNTIL_MS, value).apply()
        }

    /** 触发冷却的版本号；仅用于可读性与后续扩展。 */
    var snoozedVersionCode: Int
        get() = prefs.getInt(KEY_SNOOZED_VERSION_CODE, 0)
        set(value) {
            prefs.edit().putInt(KEY_SNOOZED_VERSION_CODE, value).apply()
        }

    companion object {
        private const val PREFS = "owlhouse_update"
        private const val KEY_IGNORED = "ignored_version_code"
        private const val KEY_SNOOZE_UNTIL_MS = "snooze_until_ms"
        private const val KEY_SNOOZED_VERSION_CODE = "snoozed_version_code"
    }
}
