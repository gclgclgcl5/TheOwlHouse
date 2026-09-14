package com.owlhouse.reader.data.api

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

private val errorJson = Json { ignoreUnknownKeys = true; isLenient = true }

/**
 * 把网络/HTTP 异常转成用户可读的中文提示。
 * 优先解析 FastAPI 的 `{"detail": "..."}` 或校验错误列表。
 */
fun userFacingError(e: Throwable, fallback: String): String {
    when (e) {
        is HttpException -> {
            val fromBody = parseFastApiDetail(e)
            if (!fromBody.isNullOrBlank()) return fromBody
            return when (e.code()) {
                400 -> "请求无效，请检查输入"
                401 -> "登录已失效，请重新登录"
                403 -> "没有权限"
                404 -> "内容不存在"
                413 -> "文件过大"
                in 500..599 -> "服务器繁忙，请稍后再试"
                else -> fallback
            }
        }
        is UnknownHostException -> return "无法连接服务器，请检查网络与电脑 IP"
        is SocketTimeoutException -> return "连接超时，请稍后重试"
        is IOException -> return "网络异常，请检查网络后重试"
        else -> {
            val msg = e.message?.trim().orEmpty()
            if (msg.isBlank()) return fallback
            if (msg.startsWith("HTTP ", ignoreCase = true) ||
                msg.contains("Bad Request", ignoreCase = true) ||
                msg.contains("Unauthorized", ignoreCase = true)
            ) {
                return fallback
            }
            return msg
        }
    }
}

private fun parseFastApiDetail(e: HttpException): String? {
    val raw = try {
        e.response()?.errorBody()?.string()
    } catch (_: Exception) {
        null
    }?.trim().orEmpty()
    if (raw.isEmpty()) return null
    return try {
        when (val root = errorJson.parseToJsonElement(raw)) {
            is JsonObject -> {
                when (val detail = root["detail"]) {
                    is JsonPrimitive -> detail.contentOrNull?.takeIf { it.isNotBlank() }
                    is JsonArray -> detail.mapNotNull { el ->
                        when (el) {
                            is JsonObject -> el["msg"]?.let { m ->
                                (m as? JsonPrimitive)?.contentOrNull
                            }
                            is JsonPrimitive -> el.contentOrNull
                            else -> null
                        }
                    }.filter { !it.isNullOrBlank() }.joinToString("；").ifBlank { null }
                    else -> null
                }
            }
            is JsonPrimitive -> root.contentOrNull
            else -> null
        }
    } catch (_: Exception) {
        null
    }
}
