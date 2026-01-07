from django.urls import path
from . import views

urlpatterns = [
    path("pixel/<int:blog_id>/", views.TrackingPixelView.as_view(), name="tracking_pixel"),
    path("collect/", views.CollectEventView.as_view(), name="collect_event"),
    path("stats/<int:blog_id>/", views.BlogStatsView.as_view(), name="blog_stats"),
]
