from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # ← ВАЖНО!
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    #path('admin/', admin.site.urls),
    path('', include('tenders.urls')),
    
    # 🔹 REST API
    path('api/v1/', include('tenders.api_urls')),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# 🔹 Обслуживание медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)