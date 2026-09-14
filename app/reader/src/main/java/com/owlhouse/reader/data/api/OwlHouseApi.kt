package com.owlhouse.reader.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface OwlHouseApi {
    @GET("api/health")
    suspend fun health(): HealthResponse

    @Multipart
    @POST("api/auth/register")
    suspend fun register(
        @Part("nickname") nickname: RequestBody,
        @Part("password") password: RequestBody,
        @Part avatar: MultipartBody.Part,
    ): TokenResponse

    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): TokenResponse

    @GET("api/auth/me")
    suspend fun me(): UserOut

    @GET("api/pages")
    suspend fun listPages(
        @Query("limit") limit: Int = 20,
        @Query("offset") offset: Int = 0,
        @Query("order") order: String = "created_at",
    ): ComicPageListOut

    @GET("api/pages/{id}")
    suspend fun getPage(@Path("id") id: Int): ComicPageOut

    @GET("api/pages/{id}/comments")
    suspend fun listComments(
        @Path("id") pageId: Int,
        @Query("sort") sort: String = "latest",
    ): CommentListOut

    @POST("api/pages/{id}/comments")
    suspend fun createComment(
        @Path("id") pageId: Int,
        @Body body: CommentCreate,
    ): CommentOut

    @POST("api/comments/{id}/like")
    suspend fun likeComment(@Path("id") commentId: Int): LikeStateOut

    @DELETE("api/comments/{id}/like")
    suspend fun unlikeComment(@Path("id") commentId: Int)

    @GET("api/notifications")
    suspend fun listNotifications(
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0,
    ): NotificationListOut

    @GET("api/notifications/unread-count")
    suspend fun unreadCount(): UnreadCountOut

    @POST("api/notifications/{id}/read")
    suspend fun markNotificationRead(@Path("id") id: Int): NotificationOut

    @POST("api/notifications/read-all")
    suspend fun markAllNotificationsRead(): MarkAllReadOut

    @GET("api/app-update")
    suspend fun getAppUpdate(): AppUpdateOut

    @GET("api/home-announcement")
    suspend fun getHomeAnnouncement(): HomeAnnouncementOut
}

@Serializable
data class HealthResponse(
    val status: String,
    val service: String? = null,
)

@Serializable
data class TokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    val role: String,
)

@Serializable
data class LoginRequest(
    val nickname: String,
    val password: String,
)

@Serializable
data class UserOut(
    val id: Int,
    val nickname: String,
    @SerialName("avatar_url") val avatarUrl: String,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class ComicPageOut(
    val id: Int,
    val title: String,
    @SerialName("page_no") val pageNo: Int,
    @SerialName("image_url") val imageUrl: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class ComicPageListOut(
    val items: List<ComicPageOut>,
    val total: Int,
    val limit: Int,
    val offset: Int,
)

@Serializable
data class CommentCreate(
    val content: String,
    @SerialName("parent_id") val parentId: Int? = null,
)

@Serializable
data class CommentOut(
    val id: Int,
    @SerialName("page_id") val pageId: Int,
    val content: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("like_count") val likeCount: Int,
    @SerialName("liked_by_me") val likedByMe: Boolean,
    @SerialName("author_id") val authorId: Int,
    @SerialName("author_nickname") val authorNickname: String,
    @SerialName("author_avatar_url") val authorAvatarUrl: String = "",
    @SerialName("author_deleted") val authorDeleted: Boolean = false,
    @SerialName("parent_id") val parentId: Int? = null,
    @SerialName("reply_to_id") val replyToId: Int? = null,
    @SerialName("reply_to_nickname") val replyToNickname: String? = null,
    @SerialName("reply_to_author_deleted") val replyToAuthorDeleted: Boolean = false,
    val replies: List<CommentOut> = emptyList(),
)

@Serializable
data class CommentListOut(
    val items: List<CommentOut>,
)

@Serializable
data class LikeStateOut(
    val liked: Boolean,
    @SerialName("like_count") val likeCount: Int,
)

@Serializable
data class NotificationOut(
    val id: Int,
    val type: String,
    @SerialName("is_read") val isRead: Boolean,
    @SerialName("created_at") val createdAt: String,
    @SerialName("actor_nickname") val actorNickname: String,
    @SerialName("actor_avatar_url") val actorAvatarUrl: String = "",
    @SerialName("actor_deleted") val actorDeleted: Boolean = false,
    @SerialName("page_id") val pageId: Int,
    @SerialName("comment_id") val commentId: Int? = null,
    @SerialName("comment_preview") val commentPreview: String = "",
    val summary: String,
)

@Serializable
data class NotificationListOut(
    val items: List<NotificationOut>,
    val total: Int,
    val limit: Int,
    val offset: Int,
)

@Serializable
data class UnreadCountOut(
    val count: Int,
)

@Serializable
data class MarkAllReadOut(
    val updated: Int,
)

@Serializable
data class AppUpdateOut(
    @SerialName("version_code") val versionCode: Int,
    @SerialName("version_name") val versionName: String = "",
    @SerialName("download_url") val downloadUrl: String = "",
    val message: String = "",
    @SerialName("updated_at") val updatedAt: String? = null,
    val available: Boolean = false,
)

@Serializable
data class HomeAnnouncementOut(
    val title: String,
    @SerialName("updated_at") val updatedAt: String? = null,
)
