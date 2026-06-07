# tenders/api/serializers.py
from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from ..models import Tender, Client
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
    profit = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )

    
    # 🔹 Увеличили max_digits до 10 (наценка может быть > 1000%)
    markup = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True,
        allow_null=True,
        coerce_to_string=False  # 🔹 Возвращаем число, не строку
    )
    
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
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
    
    
    def to_representation(self, instance):
        """Безопасная сериализация вычисляемых полей"""
        data = super().to_representation(instance)
        
        # 🔹 Безопасно конвертируем profit
        try:
            profit = instance.profit
            data['profit'] = float(profit) if profit is not None else None
        except (InvalidOperation, TypeError, ValueError):
            data['profit'] = None
        
        # 🔹 Безопасно конвертируем markup
        try:
            markup = instance.markup
            data['markup'] = float(markup) if markup is not None else None
        except (InvalidOperation, TypeError, ValueError):
            data['markup'] = None
        
        return data
    
    def validate(self, data):
        """Валидация: себестоимость не может превышать сумму контракта"""
        if data.get('cost') and data.get('final_amount'):
            if data['cost'] > data['final_amount']:
                raise serializers.ValidationError(
                    {"cost": "Себестоимость не может превышать итоговую сумму"}
                )
        return data