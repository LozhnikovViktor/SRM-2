import requests

token = '22dd012a095021d42fa3026ec11a7c13d3233666eedf0c315cc48463f1dce1ade45795be1a9c5633c06fae670a3186ffe971ed6392c56e3328c430feb15b3cd3'  # ← Вставьте ваш токен
url = 'https://tenderplan.ru/api/search/v2/list'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
}

data = {
    'query': 'поставки',
    'limit': 5,
}

response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")