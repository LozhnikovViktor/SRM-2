import xlsxwriter
from io import BytesIO
from django.utils import timezone
from .models import Tender
from django.db import models  # ← ДОБАВЬТЕ ЭТУ СТРОК
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime
import time
from decimal import Decimal
import requests
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import re


import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import re
from decimal import Decimal
from django.utils import timezone


import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import re
from decimal import Decimal
from django.utils import timezone
import random


def search_tenders_on_zakupki(keyword, region=None, max_results=20, only_active=True):
    """
    Поиск тендеров (демо-версия с реалистичными данными)
    
    В production-версии здесь будет реальное подключение к API zakupki.gov.ru
    или другому агрегатору тендеров (Сбер А, Тендер.ру, B2B-Center).
    """
    now = timezone.now()
    
    print(f"\n🔍 ДЕМО ПОИСК: {keyword}")
    print(f"🕐 Текущее время: {now}")
    
    # 🔹 Реалистичные шаблоны тендеров для демонстрации
    templates = [
        {
            'title_template': 'Поставка {keyword} для государственных нужд',
            'customer': ['ГБУЗ "Городская клиническая больница №1"', 
                        'МБОУ "Средняя общеобразовательная школа №45"',
                        'Администрация городского округа',
                        'ФГБУ "Научно-исследовательский институт"',
                        'ГКУ "Центр государственных услуг"'],
            'price_range': (50000, 5000000),
        },
        {
            'title_template': 'Выполнение работ по {keyword}',
            'customer': ['ГБУ "Жилищник района"',
                        'ФКУ Упрдор "Прикамье"',
                        'ГКУЗ "Стоматологическая поликлиника"',
                        'МБУК "Дворец культуры"',
                        'ГБОУ ВО "Московский государственный университет"'],
            'price_range': (100000, 15000000),
        },
        {
            'title_template': 'Оказание услуг по обслуживанию {keyword}',
            'customer': ['ФГБУК "Государственный музей"',
                        'ГБУЗ "Поликлиника №7"',
                        'МБУ "Управление капитального строительства"',
                        'ГКОУ ДО "Детская школа искусств"',
                        'ФГБУ "Росрезерв"'],
            'price_range': (30000, 2000000),
        },
    ]
    
    tenders = []
    
    # Генерируем реалистичные тендеры
    for i in range(min(max_results, 15)):
        template = random.choice(templates)
        
        # Генерируем будущее время дедлайна (от 3 дней до 60 дней)
        days_ahead = random.randint(3, 60)
        deadline = now + timedelta(days=days_ahead, hours=random.randint(1, 23))
        
        # Генерируем цену
        min_price, max_price = template['price_range']
        price = Decimal(str(random.randint(int(min_price), int(max_price))))
        
        # Формируем номер закупки (как на zakupki.gov.ru)
        year = now.year
        external_id = f"{random.randint(1000000, 9999999):07d}{year % 100}000{random.randint(10, 99)}"
        
        tender = {
            'title': template['title_template'].format(keyword=keyword),
            'customer_name': random.choice(template['customer']),
            'external_id': external_id,
            'source_url': f'https://zakupki.gov.ru/epz/order/notice/{external_id}.html',
            'description': f'Закупка {keyword} для государственных/муниципальных нужд. '
                f'Способ определения поставщика: электронный аукцион. '
                f'Начальная (максимальная) цена контракта: {price} руб.',
            'initial_amount': price,
            'deadline': deadline,
            'pub_date': (now - timedelta(days=random.randint(1, 10))).strftime('%d.%m.%Y'),
        }
        tenders.append(tender)
    
    # Сортируем по дедлайну
    tenders.sort(key=lambda x: x['deadline'])
    
    print(f"✅ Сгенерировано актуальных тендеров: {len(tenders)}")
    for t in tenders[:3]:
        print(f"   - {t['deadline'].strftime('%d.%m.%Y')}: {t['title'][:60]}")
    
    return tenders

def export_tenders_to_excel(tenders_qs):
    """Экспорт списка тендеров в Excel"""
    output = BytesIO()
    
    with xlsxwriter.Workbook(output, {'in_memory': True, 'remove_timezone': True}) as workbook:
        worksheet = workbook.add_worksheet('Тендеры')
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'dd.mm.yyyy'})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        
        # Заголовки
        headers = [
            'ID', 'Заказчик', 'Исполнитель', 'Начальная сумма',
            'Дедлайн', 'Статус', 'Победитель', 'Финальная сумма',
            'Затраты', 'Прибыль', 'Комментарий'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Данные
        for row, tender in enumerate(tenders_qs, start=1):
            profit = (tender.final_amount - tender.cost) if tender.final_amount and tender.cost else None
            
            worksheet.write(row, 0, tender.id, cell_format)
            worksheet.write(row, 1, tender.customer_name or '', cell_format)
            worksheet.write(row, 2, tender.executor_name or '', cell_format)
            worksheet.write(row, 3, float(tender.initial_amount) if tender.initial_amount else 0, money_format)
            worksheet.write(row, 4, tender.deadline, date_format if tender.deadline else cell_format)
            worksheet.write(row, 5, tender.status, cell_format)
            worksheet.write(row, 6, tender.winner or '', cell_format)
            worksheet.write(row, 7, float(tender.final_amount) if tender.final_amount else 0, money_format)
            worksheet.write(row, 8, float(tender.cost) if tender.cost else 0, money_format)
            worksheet.write(row, 9, profit, money_format if profit else cell_format)
            worksheet.write(row, 10, tender.comment or '', cell_format)  # ← добавили
        
        # Автоширина колонок
        worksheet.set_column(0, 0, 5)
        worksheet.set_column(1, 2, 20)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 12)
        worksheet.set_column(5, 5, 12)
        worksheet.set_column(6, 9, 15)
        worksheet.set_column(10, 10, 30)  # ← добавили (ширина для комментария)
    
    output.seek(0)
    return output


def export_dashboard_stats_to_excel():
    """Экспорт статистики дашборда в Excel"""
    output = BytesIO()
    
    with xlsxwriter.Workbook(output, {'in_memory': True}) as workbook:
        # Лист 1: Общая статистика
        summary_sheet = workbook.add_worksheet('Общая статистика')
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2196F3',
            'font_color': 'white',
            'border': 1
        })
        
        # Статистика
        total = Tender.objects.count()
        won = Tender.objects.filter(status='won').count()
        active = Tender.objects.filter(status__in=['submitted', 'published']).count()
        
        stats = [
            ['Всего тендеров', total],
            ['Выиграно', won],
            ['Активных', active],
            ['Конверсия', f'{(won/total*100):.1f}%' if total > 0 else '0%'],
        ]
        
        for row, (label, value) in enumerate(stats):
            summary_sheet.write(row, 0, label, header_format)
            summary_sheet.write(row, 1, value, workbook.add_format({'border': 1}))
        
        # Лист 2: По статусам
        status_sheet = workbook.add_worksheet('По статусам')
        
        statuses = Tender.objects.values('status').annotate(count=models.Count('id'))
        
        status_sheet.write(0, 0, 'Статус', header_format)
        status_sheet.write(0, 1, 'Количество', header_format)
        
        for row, item in enumerate(statuses, start=1):
            status_sheet.write(row, 0, item['status'], workbook.add_format({'border': 1}))
            status_sheet.write(row, 1, item['count'], workbook.add_format({'border': 1}))
    
    output.seek(0)
    return output