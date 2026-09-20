package com.owlhouse.reader.ui

import android.content.Context
import android.media.MediaPlayer
import com.owlhouse.reader.R

object WelcomeSound {
    fun play(context: Context) {
        try {
            val player = MediaPlayer.create(context.applicationContext, R.raw.welcome)
                ?: return
            player.setOnCompletionListener { mp ->
                try {
                    mp.release()
                } catch (_: Exception) {
                }
            }
            player.setOnErrorListener { mp, _, _ ->
                try {
                    mp.release()
                } catch (_: Exception) {
                }
                true
            }
            player.start()
        } catch (_: Exception) {
            /* ignore — never block login/register */
        }
    }
}
