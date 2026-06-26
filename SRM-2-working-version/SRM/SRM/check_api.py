import requests
import sys
sys.path.insert(0, '..')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SRM.settings')

import django
django.setup()

from django.conf import settings

token = settings.TENDERPLAN_API_TOKEN
print(f"🔑 Токен: {token[:20]}...")

url = 'https://tenderplan.ru/api/search/v2/list'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
}

data = {
    'query': 'поставки',
    'limit': 5,
}

print(f" Запрос к API...")
response = requests.post(url, headers=headers, json=data, timeout=10)

print(f"📊 Статус: {response.status_code}")
print(f"📄 Ответ: {response.text[:500]}")