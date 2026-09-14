package com.owlhouse.reader.config

import com.owlhouse.reader.BuildConfig

object AppConfig {
    /** 来自 BuildConfig.API_BASE_URL（真机联调已指向电脑局域网 IP）。 */
    val apiBaseUrl: String = BuildConfig.API_BASE_URL

    fun mediaUrl(path: String): String {
        if (path.startsWith("http://") || path.startsWith("https://")) {
            return path
        }
        val base = apiBaseUrl.trimEnd('/')
        val rel = if (path.startsWith("/")) path else "/$path"
        return base + rel
    }
}
