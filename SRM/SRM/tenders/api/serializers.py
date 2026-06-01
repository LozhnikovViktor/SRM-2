# tenders/api/serializers.py
from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from ..models import Tender


class TenderSerializer(serializers.ModelSerializer):
    """Сериализатор для тендера"""
    
    # 🔹 Вычисляемые поля (только для чтения)
    profit = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True,
        allow_null=True,
        coerce_to_string=False  # 🔹 Возвращаем число, не строку
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
            'id', 
            'customer_name', 
            'initial_amount', 
            'deadline', 
            'status', 
            'status_display', 
            'executor_name', 
            'procedure_url',
            'winner', 
            'final_amount', 
            'cost', 
            'profit', 
            'markup',
            'author'
        ]
        read_only_fields = ['author', 'profit', 'markup']
    
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