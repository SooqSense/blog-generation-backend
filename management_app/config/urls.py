from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# from api import views as api_views # No longer needed for home_view here
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),  # Include your app's API URLs
    path("auth/", include("authentication.urls")),  # Include authentication URLs
    # drf-spectacular URLs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # path('', api_views.home_view, name='home'), # Removed old home view
]

# Serve static files in production (usually handled by web server like nginx)
if (
    settings.DEBUG or True
):  # Force serving static files in production for this deployment
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
