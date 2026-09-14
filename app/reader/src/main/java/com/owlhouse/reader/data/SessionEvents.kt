package com.owlhouse.reader.data

import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/**
 * 会话失效信号：OkHttp 遇到 401 清 Token 后递增 generation，UI 观察后跳转登录。
 */
object SessionEvents {
    private val generation = AtomicInteger(0)
    private val pendingForceLogout = AtomicBoolean(false)

    fun currentGeneration(): Int = generation.get()

    fun markUnauthorized() {
        pendingForceLogout.set(true)
        generation.incrementAndGet()
    }

    fun consumeForceLogout(): Boolean {
        return pendingForceLogout.compareAndSet(true, false)
    }
}
