from django.urls import path
from . import views

urlpatterns = [
    path('', views.detection_page, name='detection_page'),
    path('video-feed/', views.video_feed, name='video_feed'),
    path('process-frame/', views.process_frame, name='process_frame'),
]
