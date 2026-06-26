from celery import shared_task
from .models import ShipmentRequest
from .integrations.onec import export_shipment_to_1c

@shared_task(bind=True, max_retries=3)
def export_shipment_task(self, shipment_id):
    """Фоновая задача выгрузки заявки в 1С"""
    try:
        shipment = ShipmentRequest.objects.get(id=shipment_id)
        result = export_shipment_to_1c(shipment)
        
        if not result["success"]:
            # Повторная попытка через 60 секунд
            raise self.retry(exc=Exception(result["error"]), countdown=60)
        
        return result
    
    except ShipmentRequest.DoesNotExist:
        return {"success": False, "error": "Заявка не найдена"}