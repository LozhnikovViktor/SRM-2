from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .integrations.dadata import get_company_by_inn


@api_view(['GET'])
def suggest_client_by_inn(request):
    """Проверка ИНН через DaData"""
    inn = request.query_params.get('inn', '').strip()
    
    if not inn or len(inn) not in [10, 12] or not inn.isdigit():
        return Response(
            {'error': 'ИНН должен содержать 10 или 12 цифр'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверка, что ключи настроены
    if not getattr(settings, 'DADATA_API_TOKEN', None):
        return Response(
            {'error': 'DaData API ключи не настроены в settings.py'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Запрос к реальному API DaData
    try:
        company_data = get_company_by_inn(inn)
        if not company_data:
            return Response(
                {'error': 'Компания не найдена в ЕГРЮЛ'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(company_data)
    except Exception as e:
        return Response(
            {'error': f'Ошибка API: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )