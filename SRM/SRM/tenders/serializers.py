# tenders/serializers.py
from rest_framework import serializers
from .models import Tender, TenderStatus

class TenderSerializer(serializers.ModelSerializer):
    """Сериализатор для тендера"""
    
    # Добавляем вычисляемые поля (только для чтения)
    profit = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    markup = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    
    class Meta:
        model = Tender
        fields = [
            'id', 'customer_name', 'initial_amount', 'deadline', 
            'status', 'status_display', 'executor_name', 'procedure_url',
            'winner', 'final_amount', 'cost', 'profit', 'markup',
            'author', 'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at', 'profit', 'markup']
    
    def validate(self, data):
        """Валидация: себестоимость не может превышать сумму контракта"""
        if data.get('cost') and data.get('final_amount'):
            if data['cost'] > data['final_amount']:
                raise serializers.ValidationError(
                    "Себестоимость не может превышать итоговую сумму"
                )
        return data