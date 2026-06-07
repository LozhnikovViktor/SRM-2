from rest_framework import serializers
from .models import Tender, Client
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class ClientSerializer(serializers.ModelSerializer):
    """Сериализатор для клиентов"""
    manager = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'inn', 'email', 'phone', 
            'contact_person', 'contact_position',
            'manager', 'address', 'website', 'notes', 
            'status', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class TenderSerializer(serializers.ModelSerializer):
    """Сериализатор для тендеров"""
    author = UserSerializer(read_only=True)
    client = ClientSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    # Вычисляемые поля
    profit = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    markup = serializers.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        read_only=True
    )
    
    class Meta:
        model = Tender
        fields = [
            'id', 'client', 'client_id', 'customer_name', 'initial_amount',
            'deadline', 'status', 'executor_name', 'procedure_url',
            'winner', 'final_amount', 'cost', 'profit', 'markup',
            'comment', 'author', 'source_url', 'external_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Автоматически устанавливаем автора
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)