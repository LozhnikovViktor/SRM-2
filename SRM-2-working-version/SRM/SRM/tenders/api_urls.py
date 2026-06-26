from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views
from . import dadata_views

router = DefaultRouter()
router.register(r'tenders', api_views.TenderViewSet, basename='tender')
router.register(r'clients', api_views.ClientViewSet, basename='client')
router.register(r'shipments', api_views.ShipmentRequestViewSet, basename='shipment')

urlpatterns = [
    path('clients-suggest/', dadata_views.suggest_client_by_inn, name='client-suggest'),
    path('', include(router.urls)),
]