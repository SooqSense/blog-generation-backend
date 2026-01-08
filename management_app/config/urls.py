from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Authentication URLs
    path("auth/", include("management_app.authentication.urls")),
    
    # Modular app URLs
    path("blogs/", include("management_app.blog_generator.urls")),
    path("news/", include("management_app.ai_news.urls")),
    path("image-generation/", include("management_app.image_generator.urls")),
    path("linkedin/", include("management_app.linkedin_post_generator.urls")),
    path("schedule/", include("management_app.schedule_linkedin_post.urls")),
    path("trends/", include("management_app.ai_trends.urls")),
    path("knowledge-base/", include("management_app.knowledge_base.urls")),
    path("chat/", include("management_app.chatbot.urls")),
    path("upwork/", include("management_app.upwork_proposal_generator.urls")),
    path("analytics/", include("management_app.analytics.urls")),
    
    # Shared / External API
    path("api/external/", include("management_app.shared.urls")),
    
    # drf-spectacular URLs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Health check
    path("health/", lambda r: HttpResponse("OK"), name="health"),
]

