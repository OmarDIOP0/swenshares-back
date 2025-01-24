from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'announcements', views.AnnouncementViewSet)
router.register(r'notifications', views.NotificationViewSet)
router.register(r'dividends', views.DividendViewSet)

app_name = 'sharedapp'

urlpatterns = [
    path('', include(router.urls)),
]