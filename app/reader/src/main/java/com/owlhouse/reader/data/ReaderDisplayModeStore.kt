package com.owlhouse.reader.data

/** 阅读页按图片高宽比自动选择条漫 / 整页。 */
object ReaderDisplayMode {
    /** 高宽比（height/width）达到该阈值时走条漫（宽适配 + 纵滚）。 */
    const val STRIP_ASPECT_THRESHOLD = 2.0f

    fun effectiveStrip(heightOverWidth: Float?): Boolean {
        return (heightOverWidth ?: 0f) >= STRIP_ASPECT_THRESHOLD
    }
}
