# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PhysicalShareholderViewSet,
    LegalShareholderViewSet,
    ShareViewSet,
)

router = DefaultRouter()
router.register(r'physical', PhysicalShareholderViewSet, basename='physical-shareholder')
router.register(r'legal', LegalShareholderViewSet, basename='legal-shareholder')
router.register(r'shares', ShareViewSet, basename='shares')

app_name = 'shareholders'

urlpatterns = [
    path('', include(router.urls)),
]