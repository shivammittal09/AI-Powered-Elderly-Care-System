from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("start-detection/", views.start_detection, name="start_detection"),
    path("stop-detection/", views.stop_detection, name="stop_detection"),
    path("fetch-logs/", views.fetch_logs, name="fetch_logs"),
    path("video_feed/", views.video_feed, name="video_feed"),
    path('upload-video/', views.upload_video, name='upload_video'),
    path("chat/", views.chatbot_view, name="chat"),
]
