from django.urls import path
from . import views

urlpatterns = [
    path('', views.detection_page, name='detection_page'),
    path('process-frame/', views.process_frame, name='process_frame'),
]
