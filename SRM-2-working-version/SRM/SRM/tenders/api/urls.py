from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenderViewSet

# Создаём роутер и регистрируем ViewSet
router = DefaultRouter()
router.register(r'tenders', TenderViewSet, basename='tender')

urlpatterns = [
    # Все эндпоинты будут доступны по /api/v1/tenders/
    path('', include(router.urls)),
    
    # Login/logout для browsable API (удобно для тестов в браузере)
    path('auth/', include('rest_framework.urls')),

        # 🔹 Документы тендеров

]