from django.urls import path
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({'message': 'API работает!'})

urlpatterns = [
    path('', api_root),
]