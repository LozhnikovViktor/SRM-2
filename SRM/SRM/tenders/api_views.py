from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Tender, Client
from .serializers import TenderSerializer, ClientSerializer


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