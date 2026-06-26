import requests
from django.conf import settings
from django.utils import timezone

def export_shipment_to_1c(shipment_request) -> dict:
    """Выгрузить заявку на отгрузку в 1С"""
    
    # Формируем JSON для 1С
    payload = {
        "external_id": str(shipment_request.id),
        "client_inn": shipment_request.client.inn,
        "client_name": shipment_request.client.name,
        "contact_person": shipment_request.contact_person,
        "contact_phone": shipment_request.contact_phone,
        "contact_email": shipment_request.contact_email,
        "comment": shipment_request.comment,
        "items": [
            {
                "product_article": item.product.article,
                "product_name": item.product.name,
                "quantity": float(item.quantity),
                "unit": item.product.unit,
                "unit_price": float(item.unit_price),
                "discount_percent": float(item.discount_percent),
                "final_price": float(item.final_price),
                "total": float(item.total),
            }
            for item in shipment_request.items.all()
        ]
    }
    
    try:
        response = requests.post(
            f"{settings.ONEC_API_URL}/shipment_requests",
            json=payload,
            auth=(settings.ONEC_API_USER, settings.ONEC_API_PASSWORD),
            timeout=30,
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Обновляем статус выгрузки
        shipment_request.exported_to_1c = True
        shipment_request.exported_at = timezone.now()
        shipment_request.save(update_fields=['exported_to_1c', 'exported_at'])
        
        return {"success": True, "1c_id": result.get("id")}
    
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}