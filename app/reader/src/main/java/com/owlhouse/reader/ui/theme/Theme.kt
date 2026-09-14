package com.owlhouse.reader.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

private val Scheme = darkColorScheme(
    primary = Color(0xFF6FE0D8),
    onPrimary = Color(0xFF0B1B4A),
    primaryContainer = Color(0xFF1E3A7A),
    onPrimaryContainer = Color(0xFFE1FAF8),
    secondary = Color(0xFFB8A0E8),
    onSecondary = Color(0xFF0B1B4A),
    secondaryContainer = Color(0xFF3A2F5E),
    onSecondaryContainer = Color(0xFFEEE6FF),
    tertiary = Color(0xFFFFE66A),
    onTertiary = Color(0xFF1A1A22),
    tertiaryContainer = Color(0xFF5C4E12),
    onTertiaryContainer = Color(0xFFFFF6C8),
    background = Color(0xFF0B1B4A),
    onBackground = Color(0xFFF2F6FF),
    surface = Color(0xFF152B6B),
    onSurface = Color(0xFFF2F6FF),
    surfaceVariant = Color(0xFF1E3A7A),
    onSurfaceVariant = Color(0xFFA8B8D8),
    surfaceTint = Color(0xFF6FE0D8),
    inverseSurface = Color(0xFFE8EEFF),
    inverseOnSurface = Color(0xFF0B1B4A),
    inversePrimary = Color(0xFF006A66),
    outline = Color(0xFF5A7AB8),
    outlineVariant = Color(0xFF2A4580),
    error = Color(0xFFE53935),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFF5C1A18),
    onErrorContainer = Color(0xFFFFDAD6),
    scrim = Color(0xCC000000),
)

private val OwlShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(20.dp),
    extraLarge = RoundedCornerShape(28.dp),
)

@Composable
fun OwlHouseTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = Scheme,
        shapes = OwlShapes,
        content = content,
    )
}
