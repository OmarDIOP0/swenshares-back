from rest_framework.routers import DefaultRouter
from .views import (
    IssuingCompanyViewSet, 
    SocialActViewSet,
    ActeSocialAugmentationViewSet,
    ActeSocialReductionViewSet,
    SocialeViewSet,
    TransactionViewSet
    )
from django.urls import include, path

# Initialiser le routeur
router = DefaultRouter()

# Enregistrer les ViewSets
router.register(r'issuing-companies', IssuingCompanyViewSet, basename='issuing-company')
router.register(r'social-acts', SocialActViewSet, basename='social-act')
router.register(r'capital-increases',ActeSocialAugmentationViewSet, basename="capital-increases")
router.register(r'capital-reductions', ActeSocialReductionViewSet, basename="capital-reductions")
router.register(r'social-details',SocialeViewSet,basename='social-details')
router.register(r'transactions', TransactionViewSet, basename='transactions')

# Inclure les URL générées par le routeur
urlpatterns = [
    path('', include(router.urls)),
]
