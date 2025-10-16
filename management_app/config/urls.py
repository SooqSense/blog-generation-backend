from django.contrib import admin
from django.urls import path, include
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
    path("Blogs/", include("management_app.blog_generator.urls")),
    path("News/", include("management_app.ai_news.urls")),
    path("Image Generation/", include("management_app.image_generator.urls")),
    path("Linkedin/", include("management_app.linkedin_post_generator.urls")),
    path("Schedule/", include("management_app.schedule_linkedin_post.urls")),
    path("Trends/", include("management_app.ai_trends.urls")),
    path("Knowledge Base/", include("management_app.knowledge_base.urls")),
    path("Chat/", include("management_app.chatbot.urls")),
    path("Upwork/", include("management_app.upwork_proposal_generator.urls")),
    
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
