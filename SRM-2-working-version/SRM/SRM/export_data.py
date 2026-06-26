import os
import django
from django.core.management import call_command
from io import StringIO

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SRM.settings')
django.setup()

# Экспорт данных в строку
output = StringIO()
call_command(
    'dumpdata',
    '--natural-foreign',
    '--natural-primary',
    '--indent', '2',
    stdout=output
)

# Сохранение в UTF-8
with open('data.json', 'w', encoding='utf-8') as f:
    f.write(output.getvalue())

print("✅ Данные экспортированы в data.json (UTF-8)")