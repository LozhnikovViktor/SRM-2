from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import TenderViewSet, ClientViewSet

router = DefaultRouter()
router.register(r'tenders', TenderViewSet, basename='api-tender')
router.register(r'clients', ClientViewSet, basename='api-client')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
]