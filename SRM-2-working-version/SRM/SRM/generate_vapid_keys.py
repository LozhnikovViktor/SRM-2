from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import json
import base64

# Генерируем приватный ключ
private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

# Получаем публичный ключ
public_key = private_key.public_key()

# Сериализуем в PEM формат
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

# Получаем raw public key (base64url)
public_numbers = public_key.public_numbers()
x = public_numbers.x.to_bytes(32, byteorder='big')
y = public_numbers.y.to_bytes(32, byteorder='big')
public_key_raw = b'\x04' + x + y
public_key_b64 = base64.urlsafe_b64encode(public_key_raw).rstrip(b'=').decode('utf-8')

# Сохраняем в JSON
keys = {
    'private_key': private_pem,
    'public_key': public_pem,
    'public_key_raw': public_key_b64
}

with open('vapid_keys.json', 'w', encoding='utf-8') as f:
    json.dump(keys, f, indent=2)

print('✅ VAPID ключи сгенерированы!')
print(f'Public Key (raw): {public_key_b64}')
