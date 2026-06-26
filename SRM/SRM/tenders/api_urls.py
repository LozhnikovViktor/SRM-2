from rest_framework.routers import DefaultRouter
from .api_views import TenderViewSet, ClientViewSet

router = DefaultRouter()
router.register(r'tenders', TenderViewSet, basename='tender')
router.register(r'clients', ClientViewSet, basename='client')

urlpatterns = router.urls