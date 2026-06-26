"""
Заглушка для интеграции с 1С.
Полноценная реализация будет позже.
"""

def export_shipment_to_1c(shipment_request):
    """
    Выгрузить заявку на отгрузку в 1С.
    
    Args:
        shipment_request: объект ShipmentRequest
        
    Returns:
        dict: {'success': True, '1c_id': '...'} или {'success': False, 'error': '...'}
    """
    # ВРЕМЕННАЯ ЗАГЛУШКА
    return {
        'success': False,
        'error': 'Интеграция с 1С пока не настроена'
    }