from django.urls import path
from . import views

urlpatterns = [
    path("schedule-linkedin-post/", views.schedule_linkedin_post_api, name="schedule_linkedin_post_api"),
    path("scheduled-posts/", views.get_scheduled_posts_api, name="get_scheduled_posts_api"),
    path("cancel-scheduled-post/<int:schedule_id>/", views.cancel_scheduled_post_api, name="cancel_scheduled_post_api"),
]
