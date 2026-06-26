from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Tender, Client, ShipmentRequest
from .serializers import TenderSerializer, ClientSerializer, ShipmentRequestSerializer
from .integrations.dadata import get_company_by_inn
from .tasks import export_shipment_task 
from .integrations.dadata import get_company_by_inn


class TenderViewSet(viewsets.ModelViewSet):
    """
    API endpoint для тендеров
    
    GET /api/tenders/ - список всех тендеров
    POST /api/tenders/ - создать тендер
    GET /api/tenders/{id}/ - получить тендер
    PUT /api/tenders/{id}/ - обновить тендер
    DELETE /api/tenders/{id}/ - удалить тендер
    """
    serializer_class = TenderSerializer
    permission_classes = []
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'client', 'author']
    search_fields = ['customer_name', 'executor_name', 'comment']
    ordering_fields = ['deadline', 'initial_amount', 'created_at']
    ordering = ['-deadline']
    
    def get_queryset(self):
        """Пользователь видит только свои тендеры"""
        return Tender.objects.filter(author=self.request.user).select_related('client', 'author')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        GET /api/tenders/statistics/ - статистика по тендерам
        """
        queryset = self.get_queryset()
        
        total = queryset.count()
        won = queryset.filter(status='won').count()
        active = queryset.filter(status__in=['submitted', 'published']).count()
        
        from django.db.models import Sum, F
        
        won_qs = queryset.filter(status='won')
        totals = won_qs.aggregate(
            total_final=Sum('final_amount'),
            total_cost=Sum('cost')
        )
        
        total_final = totals['total_final'] or 0
        total_cost = totals['total_cost'] or 0
        profit = total_final - total_cost
        
        return Response({
            'total': total,
            'won': won,
            'active': active,
            'win_rate': round(won / total * 100, 1) if total > 0 else 0,
            'total_profit': float(profit),
        })


class ClientViewSet(viewsets.ModelViewSet):
    """
    API endpoint для клиентов
    
    GET /api/clients/ - список всех клиентов
    POST /api/clients/ - создать клиента
    GET /api/clients/{id}/ - получить клиента
    PUT /api/clients/{id}/ - обновить клиента
    DELETE /api/clients/{id}/ - удалить клиента
    """
    serializer_class = ClientSerializer
    permission_classes = []
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'manager']
    search_fields = ['name', 'inn', 'email', 'contact_person']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        return Client.objects.select_related('manager', 'created_by')
    
    def perform_create(self, serializer):
        """Автоматически устанавливаем создателя"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def tenders(self, request, pk=None):
        """
        GET /api/clients/{id}/tenders/ - тендеры клиента
        """
        client = self.get_object()
        tenders = Tender.objects.filter(client=client).order_by('-deadline')
        serializer = TenderSerializer(tenders, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        GET /api/clients/{id}/statistics/ - статистика по клиенту
        """
        client = self.get_object()
        tenders = Tender.objects.filter(client=client)
        
        total = tenders.count()
        won = tenders.filter(status='won').count()
        
        from django.db.models import Sum, F
        profit = tenders.filter(status='won').aggregate(
            total=Sum(F('final_amount') - F('cost'))
        )['total'] or 0
        
        return Response({
            'total_tenders': total,
            'won_tenders': won,
            'win_rate': round(won / total * 100, 1) if total > 0 else 0,
            'total_profit': float(profit),
        })
    
    @action(detail=False, methods=['get'], url_path='suggest_by_inn', url_name='suggest_by_inn')
    def suggest_by_inn(self, request):
        """
        GET /api/clients/suggest_by_inn/?inn=7707083893
        """
        from django.conf import settings
        
        inn = request.query_params.get('inn', '').strip()
        if not inn:
            return Response({'error': 'ИНН обязателен'}, status=400)
        
        if len(inn) not in [10, 12] or not inn.isdigit():
            return Response({'error': 'ИНН должен быть 10 или 12 цифр'}, status=400)
        
        if Client.objects.filter(inn=inn).exists():
            return Response({'error': 'Клиент с таким ИНН уже существует'}, status=400)
        
        # Если DaData не настроен — возвращаем тестовые данные
        if not getattr(settings, 'DADATA_API_TOKEN', None):
            # Тестовые данные для ИНН 7707083893 (Сбербанк)
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
                    'name': 'ООО "Тестовая компания"',
                    'inn': '2315005197',
                    'kpp': '231501001',
                    'ogrn': '1022300000000',
                    'address': '350000, г. Краснодар, ул. Красная, д. 1',
                    'status': 'ACTIVE',
                    'status_text': '✅ Действующая',
                    'management': 'Иванов Иван Иванович',
                    'management_position': 'Генеральный директор',
                },
            }
            
            if inn in test_data:
                return Response(test_data[inn])
            return Response({
                'error': 'DaData API не настроен. Добавьте DADATA_API_TOKEN в settings.py',
                'hint': 'Для тестирования используйте ИНН: 7707083893 или 2315005197'
            }, status=500)
        
        # Запрос к DaData
        try:
            from .integrations.dadata import get_company_by_inn
            company_data = get_company_by_inn(inn)
            if not company_data:
                return Response({'error': 'Компания не найдена в ЕГРЮЛ'}, status=404)
            return Response(company_data)
        except Exception as e:
            return Response({'error': f'Ошибка API: {str(e)}'}, status=500)

class ShipmentRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint для заявок на отгрузку
    
    GET /api/shipments/ - список всех заявок
    POST /api/shipments/ - создать заявку
    GET /api/shipments/{id}/ - получить заявку
    PUT /api/shipments/{id}/ - обновить заявку
    DELETE /api/shipments/{id}/ - удалить заявку
    """
    serializer_class = ShipmentRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'client', 'exported_to_1c']
    search_fields = ['client__name', 'contact_person', 'comment']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return ShipmentRequest.objects.select_related('client', 'created_by').prefetch_related('items__product')
    
    def perform_create(self, serializer):
        """Автоматически устанавливаем создателя"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def export_to_1c(self, request, pk=None):
        shipment = self.get_object()
        if shipment.exported_to_1c:
            return Response({
                'error': 'Заявка уже выгружена в 1С',
                'exported_at': shipment.exported_at
            }, status=400)
        
        if shipment.status != 'approved':
            return Response({
                'error': 'Можно выгружать только согласованные заявки',
                'current_status': shipment.status
            }, status=400)
        
        # ВРЕМЕННО: без Celery
        # task = export_shipment_task.delay(shipment.id)
        
        return Response({
            'status': 'Выгрузка в 1С пока не настроена (Celery не установлен)',
            'message': 'Установите celery: pip install celery redis'
        }, status=202)
    
    @action(detail=True, methods=['get'])
    def export_status(self, pk=None):
        """
        GET /api/shipments/{id}/export_status/
        Проверить статус выгрузки в 1С
        """
        shipment = self.get_object()
        
        return Response({
            'exported_to_1c': shipment.exported_to_1c,
            'exported_at': shipment.exported_at,
            'status': 'Выгружена' if shipment.exported_to_1c else 'Не выгружена'
        })
    
    @action(detail=False, methods=['get'])
    def pending_export(self, request):
        """
        GET /api/shipments/pending_export/
        Список заявок, ожидающих выгрузки в 1С
        """
        pending = self.get_queryset().filter(
            exported_to_1c=False,
            status='approved'
        )
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        GET /api/shipments/statistics/
        Статистика по заявкам на отгрузку
        """
        from django.db.models import Sum, Count
        
        queryset = self.get_queryset()
        
        stats = queryset.aggregate(
            total_count=Count('id'),
            total_amount=Sum('items__final_price') * Sum('items__quantity'),
            new_count=Count('id', filter=models.Q(status='new')),
            processing_count=Count('id', filter=models.Q(status='processing')),
            approved_count=Count('id', filter=models.Q(status='approved')),
            shipped_count=Count('id', filter=models.Q(status='shipped')),
            exported_count=Count('id', filter=models.Q(exported_to_1c=True)),
        )
        
        return Response({
            'total_requests': stats['total_count'] or 0,
            'by_status': {
                'new': stats['new_count'] or 0,
                'processing': stats['processing_count'] or 0,
                'approved': stats['approved_count'] or 0,
                'shipped': stats['shipped_count'] or 0,
            },
            'exported_to_1c': stats['exported_count'] or 0,
        })