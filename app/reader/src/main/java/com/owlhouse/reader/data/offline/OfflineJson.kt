package com.owlhouse.reader.data.offline

import kotlinx.serialization.json.Json

internal val OfflineJson = Json {
    ignoreUnknownKeys = true
    isLenient = true
    encodeDefaults = true
}
