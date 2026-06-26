import os
import json
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse


# ============================================
#  PWA: View для manifest.json
# ============================================
def manifest_view(request):
    manifest_path = os.path.join(str(settings.BASE_DIR), 'static', 'pwa', 'manifest.json')
    
    try:
        # utf-8-sig автоматически удаляет BOM
        with open(manifest_path, 'r', encoding='utf-8-sig') as f:
            manifest = json.load(f)
        return JsonResponse(manifest, content_type='application/manifest+json')
    except FileNotFoundError:
        print(f"❌ Manifest not found at: {manifest_path}")
        return JsonResponse({'error': 'Manifest not found', 'path': manifest_path}, status=404)
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=500)


# ============================================
# 🔹 PWA: View для service worker
# ============================================
def sw_view(request):
    sw_path = os.path.join(str(settings.BASE_DIR), 'static', 'pwa', 'sw.js')
    
    try:
        with open(sw_path, 'r', encoding='utf-8-sig') as f:
            sw_content = f.read()
        return HttpResponse(sw_content, content_type='application/javascript')
    except FileNotFoundError:
        print(f"❌ Service Worker not found at: {sw_path}")
        return HttpResponse('Service Worker not found', status=404)

def offline_view(request):
    """Offline страница"""
    return render(request, 'offline.html')

# ============================================
# 🔹 Основные URL-маршруты
# ============================================
urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', include('tenders.urls')),
    
    # PWA файлы
    path('manifest.json', manifest_view, name='manifest'),
    path('static/pwa/sw.js', sw_view, name='service_worker'),
    path('api/', include('tenders.api_urls')),
      # Offline страница
    path('offline/', offline_view, name='offline')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)