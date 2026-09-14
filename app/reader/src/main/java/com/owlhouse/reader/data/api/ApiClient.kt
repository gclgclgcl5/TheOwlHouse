package com.owlhouse.reader.data.api

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.owlhouse.reader.config.AppConfig
import com.owlhouse.reader.data.SessionEvents
import com.owlhouse.reader.data.TokenStore
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit

object ApiClient {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    @Volatile
    private var tokenStore: TokenStore? = null

    fun init(store: TokenStore) {
        tokenStore = store
    }

    private val okHttp: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor { chain ->
                val builder = chain.request().newBuilder()
                tokenStore?.token?.takeIf { it.isNotBlank() }?.let { token ->
                    builder.header("Authorization", "Bearer $token")
                }
                chain.proceed(builder.build())
            }
            .addNetworkInterceptor { chain ->
                val response = chain.proceed(chain.request())
                if (response.code == 401) {
                    tokenStore?.clear()
                    SessionEvents.markUnauthorized()
                }
                response
            }
            .addInterceptor(
                HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BASIC
                },
            )
            .build()
    }

    val api: OwlHouseApi by lazy {
        Retrofit.Builder()
            .baseUrl(AppConfig.apiBaseUrl)
            .client(okHttp)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(OwlHouseApi::class.java)
    }
}
