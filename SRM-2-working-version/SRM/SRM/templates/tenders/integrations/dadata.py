import requests
from django.conf import settings

DADATA_API_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs"

def get_company_by_inn(inn: str) -> dict | None:
    """Получить данные компании по ИНН через DaData"""
    if not inn or len(inn) not in [10, 12]:
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
            timeout=5,
        )
        response.raise_for_status()
        
        data = response.json()
        if not data.get("suggestions"):
            return None
        
        company = data["suggestions"][0]["data"]
        return {
            "name": company["name"]["full_with_opf"],
            "inn": company["inn"],
            "kpp": company.get("kpp"),
            "ogrn": company.get("ogrn"),
            "address": company["address"]["value"] if company.get("address") else None,
            "status": company["state"]["status"],  # ACTIVE/LIQUIDATING/LIQUIDATED
            "management": company.get("management", {}).get("name"),
        }
    except Exception as e:
        print(f"DaData error: {e}")
        return None