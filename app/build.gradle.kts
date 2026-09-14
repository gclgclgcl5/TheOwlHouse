plugins {
    // 与本机已有工程对齐：AGP 8.4.2（本地 Gradle 缓存已有）+ Kotlin 1.9.24
    id("com.android.application") version "8.4.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.24" apply false
}
