from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Modular app URLs
    path("auth/", include("authentication.urls")),  # Include authentication URLs

    path("Blogs/", include("blog_generator.urls")),
    path("News/", include("ai_news.urls")),
    path("Image Generation/", include("image_generator.urls")),
    path("Linkedin/", include("linkedin_post_generator.urls")),
    path("Schedule/", include("schedule_linkedin_post.urls")),
    path("Trends/", include("ai_trends.urls")),
    path("Knowledge Base/", include("knowledge_base.urls")),
    path("Chat/", include("chatbot.urls")),
    
    # Authentication and other apps
     # Include authentication URLs
    path("Upwork/", include("upwork_proposal_generator.urls")),  # Include Upwork proposal generator URLs
    
    # drf-spectacular URLs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
