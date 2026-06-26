"""
Интеграция с DaData API для проверки ИНН и получения данных о компании.
Документация: https://dadata.ru/api/suggest/party/
"""
import requests
from django.conf import settings


DADATA_API_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs"


def get_company_by_inn(inn: str) -> dict | None:
    """
    Получить данные компании по ИНН.
    
    Возвращает словарь с полями:
    - name: полное наименование
    - inn: ИНН
    - kpp: КПП
    - ogrn: ОГРН
    - address: юридический адрес
    - status: статус (ACTIVE/LIQUIDATING/LIQUIDATED)
    - management: ФИО руководителя
    - email: email компании
    - phone: телефон компании
    """
    if not inn or len(inn) not in [10, 12] or not inn.isdigit():
        return None
    
    try:
        response = requests.post(
            f"{DADATA_API_URL}/findById/party",
            json={"query": inn, "count": 1},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {settings.DADATA_API_TOKEN}",
                "X-Secret": settings.DADATA_SECRET,
            },
            timeout=10,
        )
        response.raise_for_status()
        
        data = response.json()
        suggestions = data.get("suggestions", [])
        
        if not suggestions:
            return None
        
        company = suggestions[0]["data"]
        
        # Извлекаем данные с защитой от отсутствия полей
        name_data = company.get("name", {})
        address_data = company.get("address", {})
        state_data = company.get("state", {})
        management_data = company.get("management", {})
        
        return {
            "name": name_data.get("full_with_opf") or name_data.get("short_with_opf", ""),
            "inn": company.get("inn", ""),
            "kpp": company.get("kpp", ""),
            "ogrn": company.get("ogrn", ""),
            "address": address_data.get("value", ""),
            "status": state_data.get("status", "UNKNOWN"),
            "status_text": _get_status_text(state_data.get("status", "")),
            "management": management_data.get("name", ""),
            "management_position": management_data.get("post", ""),
            "email": company.get("emails", [None])[0] if company.get("emails") else None,
            "phone": company.get("phones", [None])[0] if company.get("phones") else None,
        }
    
    except requests.exceptions.RequestException as e:
        print(f"DaData API error: {e}")
        return None


def _get_status_text(status: str) -> str:
    """Человекочитаемый статус компании"""
    status_map = {
        "ACTIVE": "✅ Действующая",
        "LIQUIDATING": "⚠️ Ликвидируется",
        "LIQUIDATED": "❌ Ликвидирована",
        "BANKRUPT": " Банкротство",
    }
    return status_map.get(status, f"❓ {status}")