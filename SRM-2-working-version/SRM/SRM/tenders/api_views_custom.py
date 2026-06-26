from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Client


@api_view(['GET'])
def suggest_client_by_inn(request):
    """
    GET /api/clients/suggest_by_inn/?inn=7707083893
    """
    inn = request.query_params.get('inn', '').strip()
    
    if not inn:
        return Response({'error': 'ИНН обязателен'}, status=status.HTTP_400_BAD_REQUEST)
    
    if len(inn) not in [10, 12] or not inn.isdigit():
        return Response({'error': 'ИНН должен быть 10 или 12 цифр'}, status=status.HTTP_400_BAD_REQUEST)
    
    if Client.objects.filter(inn=inn).exists():
        return Response({'error': 'Клиент с таким ИНН уже существует'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Тестовые данные (если DaData не настроен)
    if not getattr(settings, 'DADATA_API_TOKEN', None):
        test_data = {
            '7707083893': {
                'name': 'ПАО "Сбербанк России"',
                'inn': '7707083893',
                'kpp': '773601001',
                'ogrn': '1027700132195',
                'address': '117997, г. Москва, ул. Вавилова, д. 19',
                'status': 'ACTIVE',
                'status_text': '✅ Действующая',
                'management': 'Греф Герман Оскарович',
                'management_position': 'Президент, Председатель Правления',
            },
            '2315005197': {
                'name': 'ООО "Кубанская компания"',
                'inn': '2315005197',
                'kpp': '231501001',
                'address': '350000, г. Краснодар, ул. Красная, д. 1',
                'status': 'ACTIVE',
                'status_text': '✅ Действующая',
            },
        }
        
        if inn in test_data:
            return Response(test_data[inn])
        
        return Response({
            'error': 'DaData API не настроен',
            'hint': 'Используйте тестовые ИНН: 7707083893 или 2315005197'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Запрос к DaData
    try:
        from .integrations.dadata import get_company_by_inn
        company_data = get_company_by_inn(inn)
        if not company_data:
            return Response({'error': 'Компания не найдена'}, status=status.HTTP_404_NOT_FOUND)
        return Response(company_data)
    except Exception as e:
        return Response({'error': f'Ошибка: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)