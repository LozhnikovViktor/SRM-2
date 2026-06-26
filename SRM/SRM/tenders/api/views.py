# tenders/api/views.py
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Tender  # 🔹 Импорт модели из родительской папки
from .serializers import TenderSerializer  # 🔹 Импорт сериализатора из текущей папки


class TenderViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с тендерами через API"""
    
    # 🔹 QuerySet с оптимизацией
    queryset = Tender.objects.select_related('author').all()
    
    # 🔹 Сериализатор
    serializer_class = TenderSerializer
    
    # 🔹 Права доступа: читать могут все, писать — только авторизованные
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    # 🔹 Бэкенды для фильтрации, поиска и сортировки
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    
    # 🔹 Поля для фильтрации в запросе: ?status=won&executor_name=ООО "Ромашка"
    filterset_fields = ['status', 'executor_name', 'winner', 'author']
    
    # 🔹 Поля для поиска: ?search=Газпром
    search_fields = ['customer_name', 'executor_name']
    
    # 🔹 Поля для сортировки: ?ordering=-deadline
    ordering_fields = ['deadline', 'initial_amount', 'created_at']
    ordering = ['-deadline']  # Сортировка по умолчанию
    
    def perform_create(self, serializer):
        """Автоматически ставим текущего пользователя автором при создании"""
        serializer.save(author=self.request.user)
    
    def get_queryset(self):
        """
        Опционально: ограничиваем доступ к тендерам.
        Раскомментируйте строку ниже, если пользователи должны видеть только свои тендеры.
        """
        queryset = super().get_queryset()
        # if not self.request.user.is_staff:
        #     queryset = queryset.filter(author=self.request.user)
        return queryset