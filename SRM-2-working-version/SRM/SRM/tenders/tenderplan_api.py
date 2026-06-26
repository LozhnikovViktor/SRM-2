"""
Модуль для работы с API Tenderplan.ru
"""
import requests
from django.conf import settings


class TenderplanAPI:
    """Клиент для работы с API Tenderplan"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'TENDERPLAN_API_URL', 'https://tenderplan.ru/api')
        self.token = getattr(settings, 'TENDERPLAN_API_TOKEN', '')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    
    def _make_request(self, method, endpoint, **kwargs):
        """Выполняет HTTP-запрос к API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method, 
                url, 
                headers=self.headers, 
                timeout=30,
                **kwargs
            )
            
            if response.status_code == 429:
                raise Exception("Превышен лимит запросов")
            
            if response.status_code == 401:
                raise Exception("Неверный токен доступа")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            raise Exception("Превышено время ожидания")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка запроса: {e}")
    
    def search_tenders(self, keyword, region=None, max_results=20):
        """Поиск тендеров по ключевому слову"""
        payload = {
            'query': keyword,
            'limit': min(max_results, 50),
            'offset': 0,
        }
        
        if region:
            payload['region'] = region
        
        try:
            data = self._make_request('POST', '/search/v2/list', json=payload)
            
            tenders = []
            items = data.get('tenders', data.get('data', data.get('items', [])))
            
            for item in items:
                tender = self._parse_tender(item)
                if tender:
                    tenders.append(tender)
            
            return tenders
            
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return []
    
    def _parse_tender(self, item):
        """Парсит данные тендера из ответа API Tenderplan"""
        if not item:
            return None
        
        # Извлекаем ID
        external_id = str(item.get('_id', item.get('id', '')))
        
        # Извлекаем название
        title = 'Тендер'
        if item.get('keys'):
            title = ', '.join(item['keys'][:3])
        elif item.get('name'):
            title = item['name']
        
        # Извлекаем заказчика
        customer_name = 'Не указан'
        customers = item.get('customers', [])
        if customers and isinstance(customers, list) and len(customers) > 0:
            customer_name = customers[0].get('name', 'Не указан')
        
        # Извлекаем цену
        initial_amount = 0
        max_price = item.get('maxPrice')
        if max_price:
            try:
                initial_amount = float(max_price)
            except (ValueError, TypeError):
                initial_amount = 0
        
        # Извлекаем дату окончания подачи (в миллисекундах!)
        deadline = None
        submission_close = item.get('submissionCloseDateTime')
        if submission_close:
            try:
                from datetime import datetime
                deadline = datetime.fromtimestamp(submission_close / 1000)
            except (ValueError, TypeError, OSError):
                deadline = None
        
        # Извлекаем регион
        region = ''
        if customers and isinstance(customers, list) and len(customers) > 0:
            region = str(customers[0].get('region', ''))
        
        # Формируем URL
        procedure_url = f"https://tenderplan.ru/tenders/{external_id}" if external_id else ''
        
        return {
            'external_id': external_id,
            'title': title[:200],
            'customer_name': customer_name[:200],
            'initial_amount': initial_amount,
            'deadline': deadline,
            'region': region,
            'procedure_url': procedure_url,
            'source': 'tenderplan.ru',
            'status': 'external',
        }
    
    def get_tender_details(self, tender_id):
        """Получает полную информацию о тендере"""
        try:
            data = self._make_request('GET', '/tenders/get', params={'id': tender_id})
            return data.get('data', data)
        except Exception as e:
            print(f"Ошибка получения деталей: {e}")
            return None
    
    def check_connection(self):
        """Проверяет подключение к API"""
        try:
            data = self._make_request('GET', '/info/status')
            return True, "Подключение успешно"
        except Exception as e:
            return False, str(e)


# Глобальный экземпляр
api_client = TenderplanAPI()