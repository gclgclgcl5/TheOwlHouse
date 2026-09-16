package com.owlhouse.reader

import android.graphics.Color as AndroidColor
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.owlhouse.reader.data.SessionEvents
import com.owlhouse.reader.ui.auth.LoginScreen
import com.owlhouse.reader.ui.auth.RegisterScreen
import com.owlhouse.reader.ui.notifications.NotificationsScreen
import com.owlhouse.reader.ui.pages.KingReaderScreen
import com.owlhouse.reader.ui.pages.PageListScreen
import com.owlhouse.reader.ui.pages.PageReaderScreen
import com.owlhouse.reader.ui.theme.OwlHouseTheme
import com.owlhouse.reader.ui.update.AppUpdatePrompt
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val nightSky = AndroidColor.parseColor("#0B1B4A")
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(AndroidColor.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(nightSky),
        )
        setContent {
            OwlHouseTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    OwlHouseNav()
                }
            }
        }
    }
}

@Composable
private fun OwlHouseNav() {
    val context = LocalContext.current
    val app = context.applicationContext as OwlHouseApp
    val navController = rememberNavController()
    var start by remember {
        mutableStateOf(if (app.tokenStore.isLoggedIn) "home" else "login")
    }
    var sessionGen by remember { mutableIntStateOf(SessionEvents.currentGeneration()) }

    fun goLogin() {
        start = "login"
        navController.navigate("login") {
            popUpTo(0) { inclusive = true }
        }
    }

    LaunchedEffect(Unit) {
        while (true) {
            delay(400)
            val gen = SessionEvents.currentGeneration()
            if (gen != sessionGen) {
                sessionGen = gen
                if (SessionEvents.consumeForceLogout() || !app.tokenStore.isLoggedIn) {
                    val route = navController.currentDestination?.route
                    if (route != "login" && route != "register") {
                        goLogin()
                    }
                }
            }
        }
    }

    NavHost(navController = navController, startDestination = start) {
        composable("login") {
            LoginScreen(
                onLoggedIn = {
                    start = "home"
                    navController.navigate("home") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onGoRegister = { navController.navigate("register") },
            )
        }
        composable("register") {
            RegisterScreen(
                onRegistered = {
                    start = "home"
                    navController.navigate("home") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onGoLogin = { navController.popBackStack() },
            )
        }
        composable("home") {
            PageListScreen(
                onOpenPage = { id -> navController.navigate("page/$id") },
                onOpenKing = { versionId, slotId ->
                    navController.navigate("king/$versionId?slotId=$slotId")
                },
                onOpenNotifications = { navController.navigate("notifications") },
                onLogout = { goLogin() },
                onSessionExpired = { goLogin() },
            )
            AppUpdatePrompt()
        }
        composable("notifications") {
            NotificationsScreen(
                onBack = { navController.popBackStack() },
                onOpenPage = { id -> navController.navigate("page/$id") },
                onOpenKing = { versionId, slotId ->
                    navController.navigate("king/$versionId?slotId=$slotId") {
                        popUpTo("notifications") { inclusive = true }
                    }
                },
                onGoHome = {
                    navController.navigate("home") {
                        popUpTo("home") { inclusive = true }
                    }
                },
                onSessionExpired = { goLogin() },
            )
        }
        composable(
            route = "page/{id}",
            arguments = listOf(navArgument("id") { type = NavType.IntType }),
        ) { entry ->
            val id = entry.arguments?.getInt("id") ?: return@composable
            PageReaderScreen(
                pageId = id,
                onBack = { navController.popBackStack() },
                onOpenPage = { nextId ->
                    navController.navigate("page/$nextId") {
                        popUpTo("page/$id") { inclusive = true }
                    }
                },
                onSessionExpired = { goLogin() },
            )
        }
        composable(
            route = "king/{versionId}?slotId={slotId}",
            arguments = listOf(
                navArgument("versionId") { type = NavType.IntType },
                navArgument("slotId") {
                    type = NavType.IntType
                    defaultValue = 0
                },
            ),
        ) { entry ->
            val versionId = entry.arguments?.getInt("versionId") ?: return@composable
            val slotId = entry.arguments?.getInt("slotId") ?: 0
            KingReaderScreen(
                versionId = versionId,
                slotId = slotId,
                onBack = { navController.popBackStack() },
                onSessionExpired = { goLogin() },
            )
        }
    }
}
