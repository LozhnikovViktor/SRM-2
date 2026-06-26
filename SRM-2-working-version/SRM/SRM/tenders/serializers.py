from rest_framework import serializers
from .models import Tender, Client, ShipmentRequest, ShipmentRequestItem
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
    
    # Вычисляемые поля через SerializerMethodField
    profit = serializers.SerializerMethodField()
    markup = serializers.SerializerMethodField()
    
    class Meta:
        model = Tender
        fields = [
            'id', 'client', 'client_id', 'customer_name', 'initial_amount',
            'deadline', 'status', 'executor_name', 'procedure_url',
            'winner', 'final_amount', 'cost', 'profit', 'markup',
            'comment', 'author', 'source_url', 'external_id',
        ]
        read_only_fields = ['id', 'author']
    
    def get_profit(self, obj):
        """Вычисляем прибыль"""
        if obj.final_amount and obj.cost:
            return float(obj.final_amount) - float(obj.cost)
        return 0
    
    def get_markup(self, obj):
        """Вычисляем наценку"""
        if obj.cost and obj.final_amount:
            profit = float(obj.final_amount) - float(obj.cost)
            return round((profit / float(obj.cost)) * 100, 1)
        return 0
    
    def create(self, validated_data):
        """Автоматически устанавливаем автора"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class ShipmentRequestItemSerializer(serializers.ModelSerializer):
    """Сериализатор для позиций заявки на отгрузку"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_article = serializers.CharField(source='product.article', read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = ShipmentRequestItem
        fields = [
            'id', 'product', 'product_name', 'product_article',
            'quantity', 'unit_price', 'discount_percent', 
            'final_price', 'total'
        ]


class ShipmentRequestSerializer(serializers.ModelSerializer):
    """Сериализатор для заявок на отгрузку"""
    items = ShipmentRequestItemSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ShipmentRequest
        fields = [
            'id', 'client', 'client_name', 'contact_person', 
            'contact_phone', 'contact_email', 'status', 'comment',
            'items', 'total_amount', 'total_quantity',
            'exported_to_1c', 'exported_at',
            'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'exported_to_1c', 'exported_at']